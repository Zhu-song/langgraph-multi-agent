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
from langgraph.types import interrupt, Send
from graph.state import AgentState
from config import llm, HIGH_RISK_TOOLS

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
import sqlite3
import hashlib
from langgraph.checkpoint.sqlite import SqliteSaver

# 🔥 【新增：重试需要的库】
import time
import uuid
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any

# ====================== ✅ 【生产级链路日志：按天文件落地】 ======================
if not os.path.exists("logs"):
    os.makedirs("logs")

today = datetime.now().strftime("%Y-%m-%d")
log_file = f"logs/agent-{today}.log"

logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.propagate = False  # 防止日志传播到 root logger 导致重复输出

# 自动补全缺失的 trace_id，避免未传 extra 时报 KeyError
class TraceIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'trace_id'):
            record.trace_id = '-'
        return True

logger.addFilter(TraceIdFilter())

formatter = logging.Formatter("%(asctime)s | %(levelname)s | [%(trace_id)s] | %(message)s")

# 文件日志
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 控制台日志
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ====================== ✅ 【统一返回格式 + 全局异常捕获】 ======================
# ====================== ✅ 【LangGraph 节点异常捕获】 ======================
# ⚠️ 注意：LangGraph 节点必须返回原始 dict（如 {"messages": [...]}），
# 不能包装成 {"code": 200, "data": ...} 格式，否则状态更新会失效
def node_try_catch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"节点异常 [{func.__name__}]: {str(e)}", extra={"trace_id": "system"})
            # 返回错误消息作为 AI 回复，保持 LangGraph 状态格式
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
    rounds = 0
    for i in range(0, len(messages)-1, 2):
        if isinstance(messages[i], HumanMessage) and isinstance(messages[i+1], AIMessage):
            rounds += 1
    return rounds

def compress_chat_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    if len(messages) < 4:
        return messages

    rounds = count_chat_rounds(messages)
    if rounds < COMPRESS_THRESHOLD:
        return messages

    split_idx = len(messages) - KEEP_LATEST * 2
    if split_idx <= 0:
        return messages

    history = messages[:split_idx]
    latest = messages[split_idx:]

    chat_text = ""
    for msg in history:
        role = "用户" if isinstance(msg, HumanMessage) else "AI"
        chat_text += f"{role}：{msg.content}\n"

    summary = llm.invoke(COMPRESS_PROMPT.format(chat_history=chat_text))
    compressed_msg = HumanMessage(content=f"【历史对话总结】{summary.content}")

    return [compressed_msg] + latest

# ====================== ✅ 【生产级：会话隔离 + 限流 + 幂等防重复】 ======================
SESSION_LIMIT_CACHE = {}
LIMIT_INTERVAL = 1.0
IDEMPOTENT_INTERVAL = 3.0

def get_question_md5(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def session_rate_idempotent(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        state = args[0]
        thread_id = state.get("configurable", {}).get("thread_id", "default_session")
        messages = state.get("messages", [])

        curr_question = ""
        if messages and hasattr(messages[-1], "content"):
            curr_question = messages[-1].content.strip()
        q_md5 = get_question_md5(curr_question)
        now = time.time()

        if thread_id not in SESSION_LIMIT_CACHE:
            SESSION_LIMIT_CACHE[thread_id] = {"last_req_time": 0, "last_q_md5": ""}
        sess = SESSION_LIMIT_CACHE[thread_id]

        if now - sess["last_req_time"] < LIMIT_INTERVAL:
            return {"messages": [SystemMessage(content="⚠️ 请求过于频繁，请稍后再试")]}
        if sess["last_q_md5"] == q_md5 and (now - sess["last_req_time"]) < IDEMPOTENT_INTERVAL:
            return {"messages": [SystemMessage(content="⚠️ 请勿重复提交相同问题")]}

        sess["last_req_time"] = now
        sess["last_q_md5"] = q_md5
        return func(*args, **kwargs)
    return wrapper

# ====================== ✅ 【Agent 链路日志装饰器】 ======================
def agent_trace_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        trace_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        logger.info(f"Agent 开始调度：{func.__name__}", extra={"trace_id": trace_id})
        try:
            result = func(*args, **kwargs)
            cost = round(time.time() - start_time, 2)
            logger.info(f"Agent 调度成功 | 耗时：{cost}s", extra={"trace_id": trace_id})
            return result
        except Exception as e:
            cost = round(time.time() - start_time, 2)
            logger.error(f"Agent 调度失败 | 耗时：{cost}s | 错误：{str(e)}", extra={"trace_id": trace_id})
            raise
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
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            result_str = str(result).lower()
            if "search" in result_str and ("failed" in result_str or "error" in result_str):
                return {"messages": [SystemMessage(content="🌐 联网搜索失败 → 一级降级：仅使用本地知识库")]}
            elif "rag" in result_str and ("no results" in result_str or "empty" in result_str):
                return {"messages": [SystemMessage(content="📚 RAG召回失败 → 二级降级：转为通用常识回答")]}
            return result
        except Exception as e:
            return {"messages": [SystemMessage(content="⚙️ 多智能体调度异常 → 三级降级：极简问答模式")]}
    return wrapper

# ==========================
# ✅ 重试装饰器
# ==========================
def retry_decorator(max_retries=3, delay_base=1):
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
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
memory = SqliteSaver(conn)

# ==========================================
# 🔥 子图：工具执行 + 人工审批
# ==========================================
def create_tool_execution_subgraph():
    subgraph_builder = StateGraph(AgentState)

    def human_approval_node(state: AgentState):
        messages = state.get("messages", [])
        if not messages:
            return {}
        last_msg = messages[-1]
        if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
            return {}

        tool_name = last_msg.tool_calls[0]["name"]
        if tool_name in HIGH_RISK_TOOLS:
            logger.warning(f"拦截高危工具调用：【{tool_name}】")
            decision = interrupt(f"审批请求: {tool_name}")
            if str(decision).lower() != "yes":
                return {"messages": [ToolMessage(
                    tool_call_id=last_msg.tool_calls[0]["id"],
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
@node_try_catch
@session_rate_idempotent
@agent_trace_log
@agent_degrade_decorator
@global_fallback_decorator
@retry_decorator(max_retries=2, delay_base=0.5)
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
    messages = state.get("messages", [])
    if not messages:
        return END
    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return [Send("tool_subgraph", {**state}) for _ in last_msg.tool_calls]
    return END

builder.add_conditional_edges("llm_agent", my_router)
builder.add_edge("tool_subgraph", "llm_agent")

graph = builder.compile(checkpointer=memory)