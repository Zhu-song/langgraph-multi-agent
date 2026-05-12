# 导入类型注解工具
# List：表示列表类型
# Dict：表示字典类型
from typing import List, Dict

# 🔥 新增：全局默认阈值
DEFAULT_SCORE_THRESHOLD = 1.5

class RAGRetriever:
    """
    🔥 RAG 检索器封装类
    功能：从向量库中检索相关文档 + 按相似度分数自动过滤低质量结果
    作用：给大模型提供干净、高相关性的上下文，提高回答准确度
    """

    def __init__(self, vector_db, score_threshold: float = DEFAULT_SCORE_THRESHOLD):
        """
        初始化 RAG 检索器
        :param vector_db: 向量数据库实例（如上面的 IncrementalChromaDB）
        :param score_threshold: 相似度分数阈值，低于该分数的结果会被过滤掉
        """
        # 保存传入的向量库对象
        self.vector_db = vector_db
        # 保存相似度过滤阈值（默认 0.45，分数越低表示越相关）
        self.score_threshold = score_threshold

    def retrieve_filtered(self, question: str, k: int = 3) -> List[Dict]:
        """
        🔥 核心方法：检索 + 过滤，返回结构化结果
        流程：向量检索 → 分数过滤 → 结构化输出
        :param question: 用户问题 / 查询语句
        :param k: 最多返回几条最相似的结果
        :return: 过滤后的文档列表，每条是字典格式（内容+元数据+分数）
        """
        # 1. 从向量库执行相似度检索，返回【文档+相似度分数】原始结果
        raw_docs = self.vector_db.similarity_search_with_score(question, k=k)
        
        # 2. 初始化过滤结果列表
        filtered = []
        
        # 3. 遍历检索结果，根据分数阈值过滤低相关性文档
        for doc, score in raw_docs:
            # 🔥 只改这一行：score <= 阈值 才是相似！
            if score <= self.score_threshold:
                # 构造成统一的字典结构，方便后续给 LLM 使用
                filtered.append({
                    "page_content": doc.page_content,  # 文档文本内容
                    "metadata": doc.metadata,          # 文档元数据（来源、页码、时间等）
                    "score": round(float(score), 2)    # 🔥 升级：保留 2 位小数
                })
        
        # 4. 返回最终过滤后的结果
        return filtered

    # 🔥 新增：调试专用 → 不带过滤，返回全部原始结果
    def get_unfiltered_results(self, question: str, k: int = 3):
        """不带过滤，仅返回所有结果（用于调试）"""
        return self.vector_db.similarity_search_with_score(question, k=k)