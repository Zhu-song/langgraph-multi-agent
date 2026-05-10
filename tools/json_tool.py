# 导入json处理模块
import json
import re
# 导入LangChain工具封装类
from langchain_core.tools import StructuredTool

# 定义JSON处理函数
def json_operate(json_str: str)->str:
    """
    JSON工具：格式化美化、格式校验、自动修复简单JSON
    传入JSON字符串，自动缩进美化并校验合法性
    """
    try:
        # 新增：从自然语言里提取 JSON
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, json_str, re.DOTALL)
        if match:
            json_str = match.group()
            # 把单引号转成双引号（标准JSON）
            json_str = json_str.replace("'", '"')
        
        # 解析JSON字符串为Python对象（校验合法性）
        data = json.loads(json_str)
        # 美化输出JSON，支持中文，缩进2格
        pretty = json.dumps(data,ensure_ascii=False,indent=2)
        # 返回美化后的结果
        return f"✅ JSON格式合法，已美化：\n{pretty}"
    except Exception as e:
        # 解析失败则返回错误信息
        return f"❌ JSON格式错误：{str(e)}"
    

# 封装为LangChain标准工具，供智能体调用
json_tool = StructuredTool.from_function(
    name="json_operate",
    func=json_operate,
    description="JSON字符串格式化美化、合法性校验、修复简易JSON格式错误"
)

# ====================== 测试代码 ======================
if __name__ == "__main__":
    print("🧪 测试 JSON 工具...\n")

    # 测试1：正常压缩JSON → 美化输出
    print("测试 1：正常 JSON")
    test1 = '{"name":"小明","age":18,"city":"北京"}'
    print(json_tool.invoke(test1))

    # 测试2：错误JSON → 捕获错误
    print("\n测试 2：错误 JSON")
    test2 = '{"name":"小明",age:18}'  # 缺少引号，格式错误
    print(json_tool.invoke(test2))

    print("\n🎉 JSON 工具测试完成！")