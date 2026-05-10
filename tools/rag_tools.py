from langchain_core.tools import StructuredTool
from rag.rag_core import rag_query

def rag_knowledge_query(question: str)->str:
    """
    私有文档RAG知识库问答工具
    用于查询本地PDF/TXT/MD私有文档内容，基于内部资料作答
    """
    return rag_query(question)

rag_tool = StructuredTool.from_function(
    name="rag_knowledge_query",
    func=rag_knowledge_query,
    description="私有文档知识库问答，查询本地内部PDF、TXT、MD文档资料"
)