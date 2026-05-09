# 旧版（保留兼容）
from .graphrag_core import build_graph_from_docs as build_graph_from_docs_old
from .graphrag_core import graph_qa as graph_qa_old

# 新版增强功能（实体归一化 + 增量 + 评分 + 来源引用）
from .builder import build_graph_from_docs
from .qa import graph_qa
from .neo4j_client import close_driver

# 对外暴露：默认使用新版！
__all__ = ["build_graph_from_docs", "graph_qa", "close_driver"]