# graphrag/settings.py - GraphRAG 模块配置
"""
GraphRAG 知识图谱模块配置

注意：此文件重命名为 settings.py 以避免与根目录 config.py 同名冲突
"""

from config import llm, NEO4J_URI, NEO4J_USER, NEO4J_PWD

# 文档目录
DOC_DIR = "./rag/docs"

# 文本分块配置
CHUNK_SIZE = 600
CHUNK_OVERLAP = 80

# 增量更新开关（True=不清空图谱，False=清空重建）
IS_INCREMENTAL = True

# 实体抽取置信度过滤阈值
ENTITY_SCORE_THRESHOLD = 0.5
