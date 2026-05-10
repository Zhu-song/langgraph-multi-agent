from langchain_core.tools import StructuredTool
import re

def text_format_convert(input_str: str)->str:
    """
    文本格式转换工具
    支持：小写转大写、大写转小写、驼峰转下划线、下划线转驼峰
    """
    # 驼峰命名 转 下划线命名（例：userName → user_name）
    def camel_to_snake(s):
        return re.sub(r'(?<!^)(?=[A-Z])','_',s).lower()
    
    # 下划线命名 转 驼峰命名（例：user_name → userName）
    def snake_to_camel(s):
        parts = s.split('_')
        return parts[0]+''.join(p.capitalize() for p in parts[1:])
    
    res_list = []
    res_list.append(f"原文本：{input_str}")
    res_list.append(f"全小写：{input_str.lower()}")
    res_list.append(f"全大写：{input_str.upper()}")
    
    # 简单判断并转换：如果包含下划线 → 转驼峰
    if "_" in input_str:
        res_list.append(f"下划线转驼峰：{snake_to_camel(input_str)}")
    # 如果包含大写字母 → 转下划线
    if re.search(r'[A-Z][a-z]',input_str):
        res_list.append(f"驼峰转下划线：{camel_to_snake(input_str)}")
    
    return "\n".join(res_list)

text_format_tool = StructuredTool.from_function(
    name="text_format_convert",
    func=text_format_convert,
    description="字符串大小写转换、驼峰命名和下划线命名互相转换，适合开发代码变量命名"
)

# ====================== 测试代码 ======================
if __name__ == "__main__":
    print("🧪 测试文本格式转换工具...\n")

    # 测试1：驼峰命名
    test1 = "userNameLangGraph"
    print("测试1：驼峰命名")
    print(text_format_tool.invoke(test1))
    print("-"*30)

    # 测试2：下划线命名
    test2 = "user_name_lang_graph"
    print("测试2：下划线命名")
    print(text_format_tool.invoke(test2))

    print("\n🎉 文本格式转换工具测试完成！")