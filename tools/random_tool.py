# 导入随机模块
import random
# 导入字符串工具模块
import string
# 导入 LangChain 工具封装类
from langchain.tools import StructuredTool

def random_generate(mode: str, length: int = 8)->str:
    """
    随机生成工具
    mode可选：
    num             -生成指定长度随机数字
    pwd             -生成大小写字母+数字的高强度密码
    choice          -从逗号分隔列表随机选一个，例：choice,苹果，香蕉，橘子
    """
    try:
        # 取出用户输入的内容（指令）
        user_input = mode.strip()
        text = user_input.lower()

        # ====================== 自然语言识别 ======================
        # 识别：生成随机数字
        if "数字" in text:
            real_mode = "num"
        
        # 识别：生成随机密码
        elif "密码" in text:
            real_mode = "pwd"
        
        # 识别：随机选择 / 抽签
        # elif "choice" in text or "随机" in text or "选" in text:
        #     real_mode = "choice"
        
        # 否则直接使用用户输入的模式
        else:
            real_mode = user_input

        # ====================== 执行逻辑 ======================
        # 模式1：生成纯数字随机数
        if real_mode == "num":
            digits = string.digits
            res = ''.join(random.choice(digits) for _ in range(length))
            return f"✅ 随机数字({length}位)：{res}"
        
        # 模式2：生成大小写+数字的随机密码
        elif real_mode == "pwd":
            chars = string.ascii_letters + string.digits
            res = ''.join(random.choice(chars) for _ in range(length))
            return f"✅ 随机密码({length}位)：{res}"
        
        # 模式3：从列表中随机选择一个
        elif real_mode.startswith("choice"):
            parts = real_mode.split(",")
            if len(parts) < 2:
                return  "❌ 格式错误，示例：choice,选项1,选项2,选项3"
            options = parts[1:]
            res = random.choice(options)
            return f"✅ 随机选中：{res}"
        
        # 不支持的模式
        else:
            return "❌ 不支持的模式：num / pwd / choice,xx,xx"
    
    # 异常捕获
    except Exception as e:
        return f"❌ 生成失败：{str(e)}"
    
# 封装成 LangChain 标准工具
random_tool = StructuredTool.from_function(
    name="random_generate",
    func=random_generate,
    description="生成随机数字、高强度随机密码、从给定选项中随机抽签"
)

# ====================== 测试代码（我加的） ======================
if __name__ == "__main__":
    print("🧪 测试随机生成工具...\n")

    # 测试1：生成随机数字
    print("测试 1：随机数字")
    print(random_tool.invoke("生成一个8位随机数字"))

    # 测试2：生成随机密码
    print("\n测试 2：随机密码")
    print(random_tool.invoke("生成一个8位随机密码"))

    # 测试3：随机选择
    print("\n测试 3：随机抽签")
    print(random_tool.invoke("choice,苹果,香蕉,橘子,西瓜"))

    print("\n🎉 随机工具测试完成！")