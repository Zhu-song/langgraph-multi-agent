# 导入rag模块
from rag import light_rag
# 导入LangChain工具封装类
from langchain.tools import StructuredTool

# 定义LightRAG双层检索函数
def lightrag_operate(question: str, mode: str = "hybrid") -> str:
    """
    LightRAG双层检索工具：Local向量检索 + Global知识图谱检索
    支持三种模式：
    - local：仅文档向量检索
    - global：仅知识图谱推理
    - hybrid：混合检索（默认，效果最强）
    """
    try:
        # 调用LightRAG统一查询入口
        answer = light_rag.query(question, mode=mode)
        # 返回最终回答
        return f"✅ LightRAG检索完成：\n{answer}"
    except Exception as e:
        # 异常捕获
        return f"❌ LightRAG检索失败：{str(e)}"


# 封装为LangChain标准工具，供智能体调用
lightrag_tool = StructuredTool.from_function(
    name="lightrag_operate",
    func=lightrag_operate,
    description="LightRAG双层检索工具，支持私有文档向量检索 + 知识图谱推理，支持local/global/hybrid三种模式"
)

# ====================== 测试代码 ======================
if __name__ == "__main__":
    print("🧪 测试 LightRAG 工具...\n")

    # 测试：混合检索（默认）
    test_question = "AI Agent开发需要学习哪些技术？"
    print(lightrag_tool.invoke({"question": test_question}))

    print("\n🎉 LightRAG 工具测试完成！")