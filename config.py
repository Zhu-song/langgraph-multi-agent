import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# 加载环境变量
load_dotenv()


# ===================== 环境变量校验 =====================
def validate_required_env_vars():
    """校验必要的环境变量是否已设置"""
    required_vars = {
        "LLM_API_KEY": "LLM API 密钥",
        "LLM_BASE_URL": "LLM API 基础 URL",
        "LLM_MODEL_NAME": "LLM 模型名称",
    }
    
    missing_vars = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var}: {desc}")
    
    if missing_vars:
        print("=" * 60)
        print("❌ 错误：缺少必要的环境变量配置")
        print("=" * 60)
        print("请在 .env 文件中配置以下变量：")
        print("\n".join(missing_vars))
        print("\n示例配置：")
        print("  LLM_API_KEY=your-api-key")
        print("  LLM_BASE_URL=https://api.openai.com/v1")
        print("  LLM_MODEL_NAME=gpt-4")
        print("=" * 60)
        sys.exit(1)


# 启动时校验
validate_required_env_vars()


# ===================== LLM 配置 =====================
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

# 初始化 LLM（兼容 OpenAI 调用）
llm = ChatOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL_NAME,
    temperature=TEMPERATURE,
    timeout=60,
    max_retries=1,
    streaming=True
)


# ===================== 嵌入模型配置 =====================
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")


# ===================== Neo4j 知识图谱配置 =====================
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PWD = os.getenv("NEO4J_PWD")


# ===================== 高危工具配置 =====================
# 高危工具列表（需要人工审核）
HIGH_RISK_TOOLS = {
    "web_search",      # 联网搜索
    "file_delete",     # 文件删除
    "file_write",      # 文件写入
    "database_write",  # 数据库写入
}


# ===================== CORS 安全配置 =====================
# 允许的跨域来源（多个域名用逗号分隔，如 "http://localhost:3000,https://example.com"）
# 生产环境请配置具体域名，不要使用 "*"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"


# ===================== 应用配置 =====================
APP_NAME = "LangGraph 多智能体助手 API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = """
基于 LangGraph 的多智能体对话系统 API

## 功能模块
- 🤖 多智能体对话（支持流式输出）
- 📚 RAG 知识库检索
- 🔍 知识图谱问答
- ✅ 人工审核机制
- 👥 多用户管理

## 认证说明
部分接口需要用户认证，请在请求头中携带有效的认证信息。
"""
