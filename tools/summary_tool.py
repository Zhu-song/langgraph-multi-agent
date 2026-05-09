#================== 长文本、文章、内容摘要 ================= 
#路由标识 summary

# 导入LangChain结构化工具封装模块
from langchain.tools import StructuredTool
# 导入项目中配置好的大模型对象
from config import llm

def long_text_summary(text: str)->str:
    """
    长文本摘要工具
    对文章、文档、日志、大段文字自动提炼核心要点、精简浓缩内容
    """
    # 构造提示词，要求模型对文本进行精简摘要，提取核心信息
    prompt = f"""
请对下面这段文本做精简摘要，提炼核心关系信息，条理清晰、简洁易懂：
{text}
"""
    # 调用大模型执行摘要生成
    res = llm.invoke(prompt)
    # 去除结果首尾空白字符，返回干净的摘要内容
    return res.content.strip()

# 将摘要函数封装为LangChain标准工具，供智能体调用
summary_tool = StructuredTool.from_function(
    name="long_text_summary",
    func=long_text_summary,
    description="对长文章、文档、日志、大段文字进行摘要提炼、精简核心内容"
)

# ====================== 测试 ======================
if __name__ == "__main__":
    print("🧪 测试长文本摘要工具...\n")

    # 测试用长文本
    test_text = """
    人工智能（AI）是指由人制造出来的系统所表现出来的智能，它是计算机科学的一个分支。
    人工智能旨在让机器能够模拟人类的感知、推理、学习等智能行为，从而替代或辅助人类完成各种复杂任务。
    近年来，随着大模型技术的发展，人工智能在自然语言处理、图像识别、智能对话等领域取得了巨大突破。
    越来越多的行业开始应用AI技术提升效率，包括教育、医疗、金融、交通、工业制造等。
    """

    print("📝 原文本：")
    print(test_text)
    print("\n🔍 摘要结果：")
    # 调用封装好的摘要工具
    print(summary_tool.invoke(test_text))

    print("\n🎉 长文本摘要工具测试通过！")