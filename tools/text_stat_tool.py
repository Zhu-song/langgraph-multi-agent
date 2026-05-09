# 导入 LangChain 工具封装类，用于创建标准工具
from langchain.tools import StructuredTool

# 定义文本统计与清洗函数
def text_stat_clean(text: str)->str:
    """
    文本统计与清洗工具
    功能：统计总字数、去除多余空格、换行、空白字符
    """
    # 文本清洗：将所有空白符（空格、换行、制表符）替换为单个空格
    clean_text = " ".join(text.split())
    # 统计清洗后的文本总字符长度
    total_len = len(clean_text)
    
    # 组装最终返回的结果信息
    res = (
        f"✅ 文本清洗完成\n"
        f"原始文本已去除多余空格、换行\n"
        f"清洗后总字符数：{total_len}\n"
        f"清洗后内容:{clean_text}"
    )
    return res


# 将清洗函数封装为 LangChain 标准工具，供智能体调用
text_stat_tool = StructuredTool.from_function(
    name="text_stat_clean",
    func=text_stat_clean,
    description="文本字数统计、去除多余空格换行、文本内容清洗预处理"
)

# ====================== 测试代码 ======================
if __name__ == "__main__":
    # 打印测试开始提示
    print("🧪 测试文本清洗与统计工具...\n")

    # 测试文本：包含大量空格、换行的混乱文本
    test_text = """
    我   爱   编程
    今天   天气很好
    学习 LangGraph  多智能体
    """

    # 调用工具执行文本清洗
    result = text_stat_tool.invoke(test_text)

    # 打印工具返回的结果
    print(result)

    # 打印测试完成提示
    print("\n🎉 文本工具测试完成！")