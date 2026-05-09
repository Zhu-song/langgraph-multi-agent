# 导入结构化工具基类，用于给 LangGraph 智能体提供调用工具
from langchain.tools import StructuredTool

# 🔥【只改这里：路径改成你真实的 rag 目录】
from rag.incremental_db import IncrementalChromaDB

# 🔥【只改这里：用你现有的 load_all_docs】
from rag.rag_core import load_all_docs

# 🔥【只改这里：删掉 file_path，你不需要传路径】
def incremental_rag_operate(is_incremental: bool = True):
    """
    知识库文档增量/全量更新操作函数
    :param is_incremental: True=增量导入（保留历史），False=全量重建（清空历史）
    :return: 操作结果提示信息
    """
    try:
        # 🔥【只改这里：直接调用你现成的函数】
        result = load_all_docs(is_incremental=is_incremental)
        return result

    # 异常捕获：导入失败时返回错误信息
    except Exception as e:
        return f"❌ 导入失败：{str(e)}"

# 封装为 LangChain 结构化工具，供 LangGraph 智能体自动调用
incremental_rag_tool = StructuredTool.from_function(
    name="incremental_rag_operate",          # 工具名称
    func=incremental_rag_operate,            # 工具执行的函数
    description="知识库增量/全量更新，is_incremental=True为增量，False为全量重建"
)