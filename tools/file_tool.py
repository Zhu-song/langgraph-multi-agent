#================== 创建 / 读取 / 追加文件、新文件夹 =================
# 路由标识：file
# 功能：本地文件/文件夹管理工具，支持创建、写入、追加、读取

import os 
from pathlib import Path
from langchain.tools import StructuredTool

# ====================== ⚠️ 安全配置：白名单目录 ======================
# 只允许操作这些目录下的文件，防止路径遍历攻击
ALLOWED_BASE_DIRS = [
    os.path.abspath("./rag/docs"),      # 知识库文档目录
    os.path.abspath("./workspace"),      # 工作目录
    os.path.abspath("./output"),         # 输出目录
    os.path.abspath("./temp"),           # 临时文件目录
]

# 最大文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024

def _is_path_allowed(file_path: str) -> tuple[bool, str]:
    """
    检查路径是否在白名单目录内
    返回: (是否允许, 错误信息)
    """
    try:
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        
        # 检查是否在白名单目录内
        for allowed_dir in ALLOWED_BASE_DIRS:
            # 确保白名单目录存在
            if not os.path.exists(allowed_dir):
                os.makedirs(allowed_dir, exist_ok=True)
            
            # 检查路径是否在允许的目录下
            try:
                Path(abs_path).resolve().relative_to(Path(allowed_dir).resolve())
                return True, ""
            except ValueError:
                continue
        
        return False, f"❌ 安全限制：只允许操作以下目录：{', '.join(ALLOWED_BASE_DIRS)}"
    
    except Exception as e:
        return False, f"❌ 路径验证失败：{str(e)}"

def file_operate(oper_type: str,file_path: str,content: str = "")->str:
    """
    文件操作核心工具
    支持功能：
    1.mkdir          创建文件夹
    2.create_file    创建文件并写入内容
    3.append_file    向文件追加内容
    4.read_file      读取文件全部内容
    
    ⚠️ 安全限制：只允许操作白名单目录下的文件
    """
    try:
        # ====================== 安全检查：路径遍历防护 ======================
        is_allowed, err_msg = _is_path_allowed(file_path)
        if not is_allowed:
            return err_msg
        
        # 创建文件夹（已存在则不报错）
        if oper_type == "mkdir":
            os.makedirs(file_path,exist_ok=True)
            return f"✅ 文件夹创建成功：{file_path}"
        
        # 创建文件并写入内容
        elif oper_type == "create_file":
            # 检查文件是否已存在
            if os.path.exists(file_path):
                return f"⚠️ 文件已存在：{file_path}，如需覆盖请先删除"
            with open(file_path,"w",encoding="utf-8") as f:
                f.write(content)
            return f"✅ 文件创建并写入成功：{file_path}"
        
        # 向已有文件追加内容
        elif oper_type == "append_file":
            if not os.path.exists(file_path):
                return f"❌ 文件不存在：{file_path}"
            with open(file_path,"a",encoding="utf-8") as f:
                f.write("\n"+content)
            return f"✅ 内容已追加到文件：{file_path}"
        
        # 读取文件内容
        elif oper_type == "read_file":
            if not os.path.exists(file_path):
                return "❌ 文件不存在"
            
            # ====================== 安全检查：文件大小限制 ======================
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                return f"❌ 文件过大（{file_size/1024/1024:.2f}MB），超过限制（{MAX_FILE_SIZE/1024/1024}MB）"
            
            with open(file_path,"r",encoding="utf-8") as f:
                return f"📄 文件内容：\n{f.read()}"
        
        # 不支持的操作类型
        else:
            return "❌ 不支持的操作类型：仅支持 mkdir / create_file / append_file / read_file"
    
    # 异常捕获，返回错误信息
    except Exception as e:
        return f"❌ 文件操作失败：{str(e)}"
    
# 封装成 LangChain 标准工具，供智能体调用
file_tool = StructuredTool.from_function(
    name="file_operate",
    func=file_operate,
    description="本地文件文件夹管理：新建文件夹、创建文件、写入内容、追加内容，读取文件"
)

# ====================== 测试 ======================
if __name__ == "__main__":
    print("🧪 测试文件操作工具...\n")

    # 测试 1：创建文件夹
    print("1. 创建文件夹")
    print(file_tool.invoke({"oper_type": "mkdir", "file_path": "test_folder"}))

    # 测试 2：创建文件
    print("\n2. 创建文件")
    print(file_tool.invoke({
        "oper_type": "create_file",
        "file_path": "test_folder/note.txt",
        "content": "这是测试内容"
    }))

    # 测试 3：追加内容
    print("\n3. 追加内容")
    print(file_tool.invoke({
        "oper_type": "append_file",
        "file_path": "test_folder/note.txt",
        "content": "追加一行新内容"
    }))

    # 测试 4：读取文件
    print("\n4. 读取文件")
    print(file_tool.invoke({"oper_type": "read_file", "file_path": "test_folder/note.txt"}))

    print("\n🎉 文件工具测试通过！")