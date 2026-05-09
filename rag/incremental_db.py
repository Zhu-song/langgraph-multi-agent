# 导入 Chroma 向量数据库（专门做文本嵌入存储 + 相似度检索）
from langchain_chroma import Chroma

# 导入嵌入模型抽象基类
# 作用：统一规范所有嵌入模型（如 OpenAIEmbeddings、智谱、阿里向量等）的接口
from langchain_core.embeddings import Embeddings

# 新增：用于文件去重、哈希记录
import os
import hashlib


class IncrementalChromaDB:
    """
    🔥 增量式 Chroma 向量数据库封装类
    功能：支持【增量添加文档】+【相似度检索】，不会覆盖旧数据
    适用场景：RAG 知识库、文档检索、长期记忆存储
    """

    def __init__(self, persist_directory: str, embedding_function: Embeddings):
        """
        初始化向量数据库
        :param persist_directory: 向量库本地保存路径（硬盘持久化）
        :param embedding_function: 向量嵌入模型（把文本转成向量）
        """
        # 创建 Chroma 实例
        # persist_directory：指定数据库存在哪个文件夹里
        # embedding_function：指定用什么模型生成向量
        self.db = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding_function
        )

        # ====================== 【新增：增量去重记录】 ======================
        self.persist_directory = persist_directory
        self.record_file = os.path.join(persist_directory, "imported_hashes.txt")
        self.imported_hashes = set()
        self._load_imported_hashes()

    # ====================== 【新增：增量去重核心逻辑】 ======================
    def _load_imported_hashes(self):
        """加载已导入的文档哈希，用于去重"""
        if os.path.exists(self.record_file):
            with open(self.record_file, "r", encoding="utf-8") as f:
                self.imported_hashes = {line.strip() for line in f if line.strip()}

    def _save_doc_hash(self, content: str):
        """保存文档哈希，避免重复导入"""
        doc_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        if doc_hash not in self.imported_hashes:
            with open(self.record_file, "a", encoding="utf-8") as f:
                f.write(doc_hash + "\n")
            self.imported_hashes.add(doc_hash)

    def is_duplicate(self, content: str) -> bool:
        """判断文档是否已导入"""
        doc_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        return doc_hash in self.imported_hashes

    # ====================== 你原有代码（完全保留） ======================
    def add_documents_incremental(self, docs):
        """
        🔥 核心功能：增量添加文档（去重版）
        特点：不会删除旧数据，只会追加新数据
        :param docs: 文档列表（Document 对象，包含 page_content 和 metadata）
        """
        # 🔥 新增：自动去重
        new_docs = []
        for doc in docs:
            if not self.is_duplicate(doc.page_content):
                new_docs.append(doc)
                self._save_doc_hash(doc.page_content)

        if new_docs:
            self.db.add_documents(new_docs)

        return len(new_docs)

    # ====================== 【新增：全量重建】 ======================
    def add_documents_full(self, docs):
        """
        🔥 全量重建：清空历史数据 → 重新导入
        """
        # 清空向量库
        self.db.delete_collection()

        # 重新初始化
        self.db = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.db._embedding_function
        )

        # 清空去重记录
        self.imported_hashes.clear()
        if os.path.exists(self.record_file):
            os.remove(self.record_file)

        # 重新写入
        return self.add_documents_incremental(docs)

    def similarity_search_with_score(self, query: str, k: int = 3):
        """
        带相似度分数的检索（RAG 最常用）
        :param query: 用户问题/检索词
        :param k: 返回最相似的前 k 条结果
        :return: 列表 [ (文档, 分数), (文档, 分数)... ]
        """
        # 执行相似度检索，同时返回匹配分数（用于判断相关性）
        return self.db.similarity_search_with_score(query, k=k)