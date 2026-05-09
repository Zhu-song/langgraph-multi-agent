# rag/lightrag.py
# 导入向量RAG问答核心函数（基于文档片段检索）
from rag.rag_core import rag_query
# 导入知识图谱问答核心函数（基于Neo4j推理）
from graphrag import graph_qa

class LightRAG:
    """
    🔥 LightRAG 核心类：实现 向量RAG + 知识图谱 双层检索
    官方标准架构：
    - local：向量检索（细粒度、事实性）
    - global：图谱检索（关联性、推理性）
    - hybrid：混合检索（最强效果）
    """
    def __init__(self):
        """初始化（无需额外参数，直接使用已初始化好的模块）"""
        pass

    def query(self, question: str, mode: str = "hybrid"):
        """
        对外统一查询入口
        :param question: 用户问题
        :param mode: 检索模式
            - local    仅向量RAG（文档检索）
            - global   仅图谱RAG（知识推理）
            - hybrid   双层检索（向量+图谱，默认）
        :return: 最终回答
        """
        if mode == "local":
            return self._query_local(question)

        elif mode == "global":
            return self._query_global(question)

        elif mode == "hybrid":
            return self._query_hybrid(question)

        else:
            return "⚠️ 模式错误：请使用 local / global / hybrid"

    def _query_local(self, question):
        """本地检索：仅调用向量RAG（基于文档块）"""
        return rag_query(question)

    def _query_global(self, question):
        """全局推理：仅调用知识图谱（基于实体关系）"""
        return graph_qa(question)

    def _query_hybrid(self, question):
        """
        🔥 混合检索（最强模式）：
        1. 先做文档检索（事实、细节）
        2. 再做图谱推理（关系、总结、推理）
        3. 图谱无结果则只返回文档答案
        """
        # 1. 向量RAG查询
        ans_rag = rag_query(question)
        # 2. 知识图谱查询
        ans_graph = graph_qa(question)

        # 3. 如果图谱无结果，只返回文档检索答案
        if "未找到" in ans_graph or "未查到" in ans_graph:
            return ans_rag

        # 4. 两边都有结果，拼接展示（文档检索 + 知识推理）
        return f"""【文档检索】\n{ans_rag}\n\n【知识推理】\n{ans_graph}"""

# ====================== 全局单例 ======================
# 创建全局 LightRAG 实例，整个项目共用一个（避免重复初始化）
light_rag = LightRAG()