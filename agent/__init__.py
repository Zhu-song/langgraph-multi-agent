# ================== Agent 模块（已废弃）==================
# ⚠️ 警告：此模块为遗留代码，已不再使用
# 
# 当前项目使用 LangGraph ReAct 架构（见 workflow.py）
# 此 Supervisor + Worker 模式已被弃用
# 
# 保留此模块仅供参考，请勿在新代码中使用
# ========================================================

import warnings

warnings.warn(
    "agent 模块已废弃，当前使用 LangGraph ReAct 架构。"
    "请使用 workflow.py 中的工作流实现。",
    DeprecationWarning,
    stacklevel=2
)

# 导出调度中枢（废弃）
from .supervisor import supervisor_agent

# 导出所有工具执行节点（废弃）
from .worker_nodes import (
    calc_worker,
    time_worker,
    translate_worker,
    summary_worker,
    search_worker,
    file_worker,
    json_worker,
    text_stat_worker,
    text_format_worker,
    random_worker,
    rag_worker,
    graphrag_worker,
    reflection_worker,
)

__all__ = [
    "supervisor_agent",
    "calc_worker",
    "time_worker",
    "translate_worker",
    "summary_worker",
    "search_worker",
    "file_worker",
    "json_worker",
    "text_stat_worker",
    "text_format_worker",
    "random_worker",
    "rag_worker",
    "graphrag_worker",
    "reflection_worker",
]
