#================== 中英文互译、技术文档翻译 ================= 
#路由标识 translate

# 导入LangChain工具封装类
from langchain.tools import StructuredTool
# 导入项目配置好的大模型实例
from config import llm

def translate_text(content: str)->str:
    """
    中英专业互译工具
    自动识别中文翻英文、英文翻中文，适合技术文档、代码注释、专业文本翻译
    """
    # 构造翻译指令：要求精准翻译，仅输出结果
    prompt = f"""
请精准专业互译，只输出翻译结果，不要多余解释、不要废话：
带翻译内容：{content}
"""
    # 调用大模型执行翻译
    res = llm.invoke(prompt)
    # 去除多余空格并返回翻译结果
    return res.content.strip()

# 封装为LangChain标准结构化工具，用于Agent调用
translate_tool = StructuredTool.from_function(
    name="translate_text",
    func=translate_text,
    description="中英文专业互译，用于翻译技术文档、代码注释、英文资料、专业文本"
)

# ====================== 测试 ======================
if __name__ == "__main__":
    print("🧪 测试翻译工具...\n")

    # 测试1：中文翻译成英文
    print("测试 1：中译英")
    print(translate_tool.invoke("知识图谱问答系统"))

    # 测试2：英文翻译成中文
    print("\n测试 2：英译中")
    print(translate_tool.invoke("Knowledge Graph Question Answering System"))

    print("\n🎉 翻译工具测试通过！")