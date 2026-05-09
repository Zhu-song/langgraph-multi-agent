# 导入类型注解工具
# Optional：表示字段可以为 None
# Sequence：表示有序列表类型（如 list、tuple）
# Annotated：用于给字段附加额外行为（如消息合并规则）
from typing import Optional, Sequence, Annotated, TypedDict, List, Dict

# 导入 LangGraph 核心工具：add_messages 用于消息自动追加合并
from langgraph.graph import add_messages

# 🔥 修复：低版本 LangGraph 不使用 State，改用 TypedDict
# from langgraph.types import State


class AgentState(TypedDict):
    """
    🔥 智能体全局状态类（整个系统的“记忆大脑”）
    所有节点（LLM、工具、审批、子图）都共享、读写这里的数据
    """

    # ==================== 核心对话消息 ====================
    # 消息列表：存储完整对话历史（用户消息、AI消息、工具调用消息）
    # Annotated[Sequence, add_messages] = 新消息自动追加，不会覆盖旧消息
    # 这是 LangGraph 多轮对话、多节点协作的核心机制
    messages: Annotated[Sequence, add_messages]

    # ==================== 业务数据字段 ====================
    # 用户当前输入的问题
    question: Optional[str]

    # 路由标识：决定智能体走哪个分支（如 search / rag / calc / translate 等）
    route: Optional[str]

    # 工具执行后的原始结果（搜索结果、计算结果、翻译结果等）
    tool_result: Optional[str]

    # 最终整理好的、给用户看的精炼答案
    final_answer: Optional[str]

    # 多轮对话历史字符串（用于给 LLM 提供长期上下文记忆）
    chat_history: Optional[str]

    # ==================== 【新增】RAG 高级功能所需字段 ====================
    # 1. 实体归一化（同义词合并）
    raw_entities: Optional[List[str]]                # 原始抽取的实体
    canonical_entities: Optional[Dict[str, str]]     # 标准化实体映射（同义词→标准名）

    # 2. LightRAG 双层检索 + 3种查询模式
    query_mode: Optional[str]                        # local / global / hybrid
    local_chunks: Optional[List[Dict]]               # 本地片段检索结果（带分数+来源）
    global_context: Optional[List[Dict]]             # 全局跨文档主题检索结果

    # 3. 相关性评分 + 阈值过滤
    score_threshold: Optional[float]                 # 相似度过滤阈值（默认 0.5）

    # 4. 增量更新知识库
    is_incremental: Optional[bool]                   # True=增量追加 False=全量重建

    # 5. 来源引用标注
    citations: Optional[List[Dict]]                  # 来源文档、片段、页码、得分

    # 6. RAG 流式输出
    stream_context: Optional[str]                    # 流式生成用的上下文