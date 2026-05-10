# 导入 LangChain 工具封装类
from langchain_core.tools import StructuredTool

# 导入核心的知识图谱问答函数
from graphrag.graphrag_core import graph_qa

def graph_knowledge_query(question: str) -> str:
    """
    知识图谱 GraphRAG 问答工具函数
    功能：用于实体关联查询、关系推理、多跳问答、架构层级关系查询
    
    参数：
        question: 用户的自然语言问题（如：张三的朋友是谁？）
    
    返回：
        知识图谱返回的答案字符串
    """
    # 调用底层知识图谱问答核心方法
    return graph_qa(question)

# 封装为 LangChain 标准结构化工具
graphrag_tool = StructuredTool.from_function(
    # 工具名称（Agent 智能体调用时使用）
    name="graph_knowledge_query",
    # 工具绑定的执行函数
    func=graph_knowledge_query,
    # 工具功能描述（非常重要：Agent 靠这个判断是否调用该工具）
    description="知识图谱问答工具，用于查询实体关系、架构层级、多跳关联推理等问题"
)