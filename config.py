import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# 加载环境变量
load_dotenv()


# 小米MiMo LLM配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0))

# 初始化小米MiMo（兼容OpenAI调用）
llm = ChatOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL_NAME,
    temperature=TEMPERATURE,
    timeout=60,
    max_retries=1,
    streaming=True
)


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
