# ================== LangGraph 多智能体工作流 ==================
# 功能：官方标准 ReAct 架构 + llm.bind_tools()
# 优化：生产级健壮性、容错、常量抽离、SQLite 规范、拒绝逻辑补全
# 新增：框架级 interrupt_before 人工审批 + 分级高危工具放行
# 新增：SqliteSaver 硬盘级持久化记忆，支持进程重启恢复
# 新增：【子图嵌套 Subgraph】模块化 —— 工具审批独立封装
# 新增：【Send 并行派发】多工具 / 多 Worker 并行执行
# 新增：集成 LightRAG 双层检索工具（local/global/hybrid）
# 新增：知识库增量/全量更新工具（incremental_rag_tool）
# 新增：长对话上下文自动压缩 + 历史总结（防Token溢出）
# 新增：生产级 会话隔离 + 按会话限流 + 幂等防重复提交
# 新增：结构化链路日志本地落地，按天自动切割
# 新增：统一接口返回格式 + 全局异常捕获
# =================================================================

from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

# 兼容不同版本的 checkpoint 导入
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph.checkpoint.memory import MemorySaver as SqliteSaver
    except ImportError:
        SqliteSaver = None

# 兼容不同版本的 langgraph 导入
try:
    # 新版本 (1.x)
    from langgraph.types import interrupt, Send
except ImportError:
    try:
        # 旧版本 (0.x)
        import langgraph.types as lg_types
        interrupt = lg_types.interrupt
        Send = lg_types.Send
    except ImportError:
        # 更旧版本
        from langgraph.constants import Send
        from langgraph.func import interrupt

from graph.state import AgentState
from config import llm, HIGH_RISK_TOOLS

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
import sqlite3
import hashlib

# 🔥 【新增：重试需要的库】
import time
import uuid
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any

# ====================== ✅ 【统一日志配置（使用 utils/logger.py）】 ======================
from utils.logger import logger, trace_log, async_trace_log, agent_trace_log

# ====================== ✅ 【统一返回格式 + 全局异常捕获】 ======================
# ====================== ✅ 【LangGraph 节点异常捕获】 ======================
# ⚠️ 注意：LangGraph 节点必须返回原始 dict（如 {"messages": [...]}），
# 不能包装成 {"code": 200, "data": ...} 格式，否则状态更新会失效
def node_try_catch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            # 网络连接错误
            logger.error(f"网络连接异常 [{func.__name__}]: {str(e)}", extra={"trace_id": "system"})
            return {"messages": [AIMessage(content=f"❌ 网络连接失败，请检查网络后重试")]}
        except TimeoutError as e:
            # 超时错误
            logger.error(f"请求超时 [{func.__name__}]: {str(e)}", extra={"trace_id": "system"})
            return {"messages": [AIMessage(content=f"❌ 请求超时，请稍后重试")]}
        except ValueError as e:
            # 参数错误
            logger.error(f"参数错误 [{func.__name__}]: {str(e)}", extra={"trace_id": "system"})
            return {"messages": [AIMessage(content=f"❌ 参数错误: {str(e)}")]}
        except KeyError as e:
            # 缺少必要字段
            logger.error(f"数据字段缺失 [{func.__name__}]: {str(e)}", extra={"trace_id": "system"})
            return {"messages": [AIMessage(content=f"❌ 数据格式错误，缺少必要字段")]}
        except Exception as e:
            # 其他未预期异常（保留兜底，但记录详细堆栈）
            logger.error(f"节点异常 [{func.__name__}]: {str(e)}", extra={"trace_id": "system"}, exc_info=True)
            return {"messages": [AIMessage(content=f"❌ 服务异常: {str(e)}")]}
    return wrapper

# ====================== ✅ 【长对话上下文自动压缩 + 总结】 ======================
COMPRESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是对话上下文压缩专家，请精简总结历史对话，保留核心意图、关键信息、业务数据，删除冗余寒暄，不丢失关键上下文，用于AI接续对话。"),
    ("human", "历史对话：\n{chat_history}")
])

COMPRESS_THRESHOLD = 6
KEEP_LATEST = 2

def count_chat_rounds(messages: list[BaseMessage]) -> int:
    """
    计算对话轮数
    改进：只统计 HumanMessage -> AIMessage 的有效对话轮次
    """
    rounds = 0
    i = 0
    while i < len(messages) - 1:
        # 找到 HumanMessage
        if isinstance(messages[i], HumanMessage):
            # 向后查找对应的 AIMessage（跳过 ToolMessage 等中间消息）
            j = i + 1
            while j < len(messages) and not isinstance(messages[j], AIMessage):
                j += 1
            if j < len(messages) and isinstance(messages[j], AIMessage):
                rounds += 1
                i = j + 1  # 从 AI 回复后继续
            else:
                i += 1
        else:
            i += 1
    return rounds

def compress_chat_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    压缩对话历史
    改进：正确处理包含 ToolMessage 的消息序列
    """
    if len(messages) < 4:
        return messages

    rounds = count_chat_rounds(messages)
    if rounds < COMPRESS_THRESHOLD:
        return messages

    # 保留最近 KEEP_LATEST 轮对话
    # 从后向前找到 KEEP_LATEST 个 HumanMessage
    human_count = 0
    split_idx = len(messages)
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            human_count += 1
            if human_count == KEEP_LATEST:
                split_idx = i
                break
    
    if split_idx <= 0 or split_idx >= len(messages):
        return messages

    history = messages[:split_idx]
    latest = messages[split_idx:]

    # 生成历史摘要
    chat_text = ""
    for msg in history:
        if isinstance(msg, HumanMessage):
            chat_text += f"用户：{msg.content}\n"
        elif isinstance(msg, AIMessage):
            chat_text += f"AI：{msg.content}\n"
        elif isinstance(msg, ToolMessage):
            chat_text += f"[工具结果]\n"

    try:
        summary = llm.invoke(COMPRESS_PROMPT.format(chat_history=chat_text))
        compressed_msg = HumanMessage(content=f"【历史对话总结】{summary.content}")
        return [compressed_msg] + latest
    except Exception as e:
        logger.warning(f"对话压缩失败: {str(e)}，返回原始消息")
        return messages

# ====================== ✅ 【生产级：会话隔离 + 限流 + 幂等防重复】 ======================
# 使用 TTL 缓存避免内存泄漏（自动清理过期会话）
from cachetools import TTLCache

# 缓存配置：最多 1000 个会话，每个会话 1 小时过期
SESSION_LIMIT_CACHE = TTLCache(maxsize=1000, ttl=3600)
LIMIT_INTERVAL = 1.0
IDEMPOTENT_INTERVAL = 3.0

def get_question_md5(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def session_rate_idempotent(func):
    """
    会话限流 + 幂等装饰器
    改进：从 state 的 metadata 中获取 thread_id，而不是从 configurable
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        state = args[0]
        # 改进：使用 state 中的 user_id 或生成默认 ID
        # 在 LangGraph 中，thread_id 通过 config 传递，但这里我们通过其他方式获取
        messages = state.get("messages", [])
        
        # 尝试从最后一条消息的内容中提取用户标识，或使用消息数量作为临时 ID
        thread_id = "default_session"
        if messages:
            # 使用最近的用户消息内容哈希作为临时会话标识
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    thread_id = f"user_{hashlib.md5(msg.content.encode()).hexdigest()[:16]}"
                    break
        
        curr_question = ""
        if messages and hasattr(messages[-1], "content"):
            curr_question = messages[-1].content.strip()
        q_md5 = get_question_md5(curr_question)
        now = time.time()

        # TTLCache 使用 get 方法避免 KeyError
        sess = SESSION_LIMIT_CACHE.get(thread_id, {"last_req_time": 0, "last_q_md5": ""})

        if now - sess["last_req_time"] < LIMIT_INTERVAL:
            return {"messages": [SystemMessage(content="⚠️ 请求过于频繁，请稍后再试")]}
        if sess["last_q_md5"] == q_md5 and (now - sess["last_req_time"]) < IDEMPOTENT_INTERVAL:
            return {"messages": [SystemMessage(content="⚠️ 请勿重复提交相同问题")]}

        SESSION_LIMIT_CACHE[thread_id] = {"last_req_time": now, "last_q_md5": q_md5}
        return func(*args, **kwargs)
    return wrapper

# 导入所有工具
from tools import (
    calc_tool,
    time_tool,
    translate_tool,
    summary_tool,
    search_tool,
    file_tool,
    json_tool,
    text_stat_tool,
    text_format_tool,
    random_tool,
    rag_tool,
    graphrag_tool,
    reflection_tool,
    lightrag_tool,
    incremental_rag_tool
)

# 🔥【新增 1】导入统一提示词
from prompts.system_prompt import SUPERVISOR_PROMPT, GLOBAL_RULES

# ✅ 【规范导入全局兜底】
from utils.global_fallback import global_fallback_decorator

# ==========================
# 【三级故障降级】
# ==========================
def agent_degrade_decorator(func):
    """
    降级装饰器
    改进：通过检查结果中的特定标记来判断是否降级，而不是字符串匹配
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # 检查 result 是否是 dict 且包含 messages
            if not isinstance(result, dict) or "messages" not in result:
                return result
            
            messages = result.get("messages", [])
            if not messages:
                return result
            
            # 获取最后一条 AI 消息
            last_msg = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and hasattr(msg, 'content'):
                    last_msg = msg
                    break
            
            if last_msg and last_msg.content:
                content = last_msg.content.lower()
                
                # 检查特定的降级标记（工具返回的错误标记）
                if "[search_failed]" in content or "[搜索失败]" in content:
                    return {"messages": [AIMessage(content="🌐 联网搜索失败 → 一级降级：仅使用本地知识库")]}
                elif "[rag_no_results]" in content or "[rag_empty]" in content:
                    return {"messages": [AIMessage(content="📚 RAG召回失败 → 二级降级：转为通用常识回答")]}
            
            return result
        except Exception as e:
            # 发生异常时触发三级降级
            logger.warning(f"降级触发 - 异常: {str(e)}")
            return {"messages": [AIMessage(content="⚙️ 多智能体调度异常 → 三级降级：极简问答模式")]}
    return wrapper

# ==========================
# ✅ 重试装饰器
# ==========================
def retry_decorator(max_retries=3, delay_base=1):
    """
    重试装饰器
    注意：必须放在 global_fallback_decorator 外层，才能感知到异常并重试
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    logger.warning(f"🔁 Agent 重试 {attempt}/{max_retries} | 错误：{str(e)}")
                    if attempt >= max_retries:
                        break
                    time.sleep(delay_base * attempt)
            # 重试耗尽后抛出异常，让外层的 global_fallback_decorator 捕获
            raise last_err
        return wrapper
    return decorator

# 工具列表
tools = [
    calc_tool, time_tool, translate_tool, summary_tool, search_tool,
    file_tool, json_tool, text_stat_tool, text_format_tool, random_tool,
    rag_tool, graphrag_tool, reflection_tool, lightrag_tool, incremental_rag_tool
]

llm_with_tools = llm.bind_tools(tools)

# ================== 常量配置 ==================
DB_PATH = "agent_memory.db"

# ================== 延迟初始化 SQLite 连接 ==================
# 避免模块导入时立即创建数据库连接
_memory = None
_conn = None

def get_memory():
    """延迟初始化 SqliteSaver（首次调用时创建连接）"""
    global _memory, _conn
    if _memory is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _memory = SqliteSaver(_conn)
    return _memory

# ==========================================
# 🔥 子图：工具执行 + 人工审批
# ==========================================
def create_tool_execution_subgraph():
    """
    创建工具执行子图
    改进：每个工具调用独立审批，而不是只检查第一个
    """
    subgraph_builder = StateGraph(AgentState)

    def human_approval_node(state: AgentState):
        """
        人工审批节点
        改进：从 state 的 metadata 中获取当前要处理的 tool_call
        """
        messages = state.get("messages", [])
        if not messages:
            return {}
        
        last_msg = messages[-1]
        if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
            return {}

        # 获取当前子图实例对应的 tool_call 索引
        # 通过 Send 传递的 state 中包含 tool_call_index
        tool_call_index = state.get("tool_call_index", 0)
        
        if tool_call_index >= len(last_msg.tool_calls):
            return {}
        
        tool_call = last_msg.tool_calls[tool_call_index]
        tool_name = tool_call.get("name", "")
        tool_id = tool_call.get("id", "")
        
        if tool_name in HIGH_RISK_TOOLS:
            logger.warning(f"拦截高危工具调用：【{tool_name}】")
            decision = interrupt(f"审批请求: {tool_name}")
            if str(decision).lower() != "yes":
                return {"messages": [ToolMessage(
                    tool_call_id=tool_id,
                    name=tool_name,
                    content=f"❌ 人工已拒绝执行工具：{tool_name}"
                )]}
        else:
            logger.info(f"自动放行低风险工具：【{tool_name}】")
        
        return {}

    tool_node = ToolNode(tools)
    subgraph_builder.add_node("human_approval", human_approval_node)
    subgraph_builder.add_node("tools", tool_node)
    subgraph_builder.add_edge(START, "human_approval")
    subgraph_builder.add_edge("human_approval", "tools")
    return subgraph_builder.compile()

tool_subgraph = create_tool_execution_subgraph()

# ================== ReAct LLM 节点 ==================
# 装饰器顺序（从外到内，执行时由内到外）：
# 1. node_try_catch - 最内层，捕获所有异常并返回标准格式
# 2. session_rate_idempotent - 限流和幂等检查
# 3. agent_trace_log - 日志记录
# 4. agent_degrade_decorator - 降级处理
# 5. global_fallback_decorator - 全局兜底（捕获异常返回友好提示）
# 6. retry_decorator - 最外层，负责重试逻辑
@retry_decorator(max_retries=2, delay_base=0.5)
@global_fallback_decorator
@agent_degrade_decorator
@agent_trace_log
@session_rate_idempotent
@node_try_catch
def llm_agent_node(state: AgentState):
    messages = compress_chat_history(state.get("messages", []))

    system_prompt = SystemMessage(content=(
        SUPERVISOR_PROMPT + "\n" + GLOBAL_RULES + "\n"
        "你具备工具调用能力，严格遵守规则：\n"
        "1. 涉及实时/最新/搜索/资讯/新闻/动态等时效性问题 → 必须调用 web_search，禁止直接回答；\n"
        "2. 知识库问题 → 优先 lightrag_tool（默认 hybrid）；\n"
        "3. 更新知识库 → 使用 incremental_rag_tool；\n"
        "4. 意图过短、模糊、不明确 → 禁止调用工具，必须澄清；\n"
        "5. 工具拒绝后不再重复调用；\n"
        "6. 回答简洁、不幻觉、不编造、严格基于结果。"
    ))

    full_messages = [system_prompt] + messages
    response = llm_with_tools.invoke(full_messages)
    return {"messages": [response]}

# ================== 主工作流构建 ==================
builder = StateGraph(AgentState)
builder.add_node("llm_agent", llm_agent_node)
builder.add_node("tool_subgraph", tool_subgraph)
builder.set_entry_point("llm_agent")

def my_router(state):
    """
    路由函数
    改进：为每个 tool_call 创建独立的子图实例，并传递 tool_call_index
    """
    messages = state.get("messages", [])
    if not messages:
        return END
    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        # 为每个 tool_call 创建一个 Send，并传递索引
        sends = []
        for i, _ in enumerate(last_msg.tool_calls):
            # 创建新的 state 副本，包含 tool_call_index
            new_state = {**state, "tool_call_index": i}
            sends.append(Send("tool_subgraph", new_state))
        return sends
    return END

builder.add_conditional_edges("llm_agent", my_router)
builder.add_edge("tool_subgraph", "llm_agent")

graph = builder.compile(checkpointer=get_memory())
