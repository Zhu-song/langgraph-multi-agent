# -*- coding: utf-8 -*-
# 设置文件编码为UTF-8，确保中文等字符正常显示

# 导入操作系统相关库，用于文件/目录操作
import os
import time
from functools import wraps

# 导入dotenv，用于加载.env文件中的环境变量（如API Key）
from dotenv import load_dotenv

# 导入文档加载器：用于读取 文本文件 / Markdown / PDF
from langchain_community.document_loaders import TextLoader, PyPDFLoader

# 导入文本分割器：将长文本切分成小块（向量库标准操作）
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入Chroma向量数据库
from langchain_chroma import Chroma

# 导入智谱AI嵌入模型，用于生成文本向量
from langchain_community.embeddings import ZhipuAIEmbeddings

# 加载.env文件中的环境变量
load_dotenv()

# ==================== 导入项目内部模块 ====================
# 导入项目配置好的大模型实例
from config import llm

# 导入自省反思模块：对AI回答进行二次校验优化
from reflection.reflection_core import reflect_answer

# 导入增量向量库封装类
from rag.incremental_db import IncrementalChromaDB

# 导入带分数过滤的检索器
from rag.retriever import RAGRetriever

# 导入来源引用格式化工具
from rag.citation import format_citation

# 🔥【新增 1】引入统一规范提示词
from prompts.system_prompt import RAG_QA_PROMPT

# ====================== ✅ 【接口限流 + 防重复请求】 ======================
REQUEST_CACHE = {}
LIMIT_INTERVAL = 1  # 1秒内只能请求1次

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not args:
            return func(*args, **kwargs)
        
        key = str(args[0])
        now = time.time()

        if key in REQUEST_CACHE and now - REQUEST_CACHE[key] < LIMIT_INTERVAL:
            return "⚠️ 请求过于频繁，请1秒后再试"

        REQUEST_CACHE[key] = now
        return func(*args, **kwargs)
    return wrapper

# ====================== ✅ 【链路日志：直接嵌入】 ======================
import uuid
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def trace_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        trace_id = str(uuid.uuid4())[:8]
        start = time.time()
        logger.info(f"[{trace_id}] 开始执行：{func.__name__} | 参数：{args}")
        try:
            res = func(*args, **kwargs)
            cost = round(time.time() - start, 2)
            logger.info(f"[{trace_id}] 执行成功：{func.__name__} | 耗时：{cost}s")
            return res
        except Exception as e:
            cost = round(time.time() - start, 2)
            logger.error(f"[{trace_id}] 执行失败：{func.__name__} | 耗时：{cost}s | 错误：{str(e)}")
            raise
    return wrapper

# ====================== ✅ 【三级降级策略：直接嵌入】 ======================
DEGRADE_LEVEL = 0  # 0=正常, 1=一级, 2=二级, 3=三级

def set_degrade(level):
    global DEGRADE_LEVEL
    DEGRADE_LEVEL = level

def degrade_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global DEGRADE_LEVEL
        try:
            res = func(*args, **kwargs)

            # 二级降级触发：RAG召回为空
            if "未找到相关" in str(res) or "无相关" in str(res):
                set_degrade(2)

            # 一级降级：搜索失败（自动识别）
            if "搜索" in str(res) and ("失败" in str(res) or "超时" in str(res)):
                set_degrade(1)

            # 降级文案
            if DEGRADE_LEVEL == 1:
                return "🌐 联网搜索不可用，已降级 → 仅使用本地知识库回答\n" + res
            elif DEGRADE_LEVEL == 2:
                return "📚 未找到专业知识，已降级 → 基于通用常识回答\n" + res
            elif DEGRADE_LEVEL == 3:
                return "⚙️ 系统调度异常，已降级 → 极简问答模式\n" + res
            return res
        except Exception as e:
            set_degrade(3)
            import traceback
            traceback.print_exc()
            return f"⚙️ 系统异常，已降级为极简问答（原因: {type(e).__name__}: {e}）"
    return wrapper

# ====================== ✅ 【重试装饰器】 ======================
def retry_decorator(max_retries=3, delay_base=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_result = None
            for attempt in range(1, max_retries + 1):
                try:
                    res = func(*args, **kwargs)
                    if res and ("未找到相关" in res or "暂无相关" in res or "无相关" in res):
                        raise Exception(f"空召回，第 {attempt} 次重试")
                    return res
                except Exception as e:
                    last_result = f"❌ 错误：{str(e)}"
                    logger.warning(f"🔁 重试 {attempt}/{max_retries} | 原因：{str(e)}")
                    if attempt >= max_retries:
                        break
                    time.sleep(delay_base * attempt)
            return last_result
        return wrapper
    return decorator

# ====================== ✅ 【全局故障兜底：直接嵌入】 ======================
def global_fallback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err = str(e).lower()
            logger.error(f"【全局兜底】异常：{err}")

            if "timeout" in err or "超时" in err:
                return "⚠️ 大模型接口请求超时，请稍后再试"
            elif "auth" in err or "key" in err or "鉴权" in err:
                return "⚠️ 接口鉴权失败，请检查API Key配置"
            elif "file" in err or "pdf" in err or "编码" in err:
                return "⚠️ 文件读取失败或格式不支持"
            elif "param" in err or "参数" in err:
                return "⚠️ 工具参数解析错误"
            elif "network" in err or "连接" in err:
                return "⚠️ 网络异常，请检查网络"
            else:
                return "⚠️ 系统暂时异常，请稍后重试"
    return wrapper

# ====================== 全局配置 ======================
CONFIG = {
    "PERSIST_DIR": "./rag/chroma_db",
    "DOC_DIR": "./rag/docs",
    "EMBEDDING_MODEL": "embedding-2",
    "CHUNK_SIZE": 800,
    "CHUNK_OVERLAP": 100,
    "SEARCH_K": 3,
    "SCORE_THRESHOLD": 1.5
}

# ====================== 初始化RAG组件 ======================
embeddings = ZhipuAIEmbeddings(
    api_key=os.getenv("ZHIPUAI_API_KEY") or os.getenv("ZHIPU_API_KEY"),
    model=CONFIG["EMBEDDING_MODEL"]
)

vector_db = IncrementalChromaDB(
    persist_directory=CONFIG["PERSIST_DIR"],
    embedding_function=embeddings
)

retriever = RAGRetriever(
    vector_db=vector_db,
    score_threshold=CONFIG["SCORE_THRESHOLD"]
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CONFIG["CHUNK_SIZE"],
    chunk_overlap=CONFIG["CHUNK_OVERLAP"]
)

# ====================== 文档加载 ======================
def load_all_docs(is_incremental: bool = True):
    try:
        os.makedirs(CONFIG["DOC_DIR"], exist_ok=True)
        files = os.listdir(CONFIG["DOC_DIR"])
        if not files:
            return "⚠️ 文档文件夹为空"

        all_docs = []
        for file in files:
            path = os.path.join(CONFIG["DOC_DIR"], file)
            try:
                if file.endswith((".txt", ".md")):
                    loader = TextLoader(path, encoding="utf-8")
                elif file.endswith(".pdf"):
                    loader = PyPDFLoader(path)
                else:
                    continue
                docs = loader.load()
                all_docs.extend(docs)
            except Exception as e:
                logger.warning(f"文件 {file} 加载失败：{str(e)}")

        if not all_docs:
            return "⚠️ 未读取到有效文档"

        split_docs = text_splitter.split_documents(all_docs)
        if is_incremental:
            added = vector_db.add_documents_incremental(split_docs)
            return f"✅ 增量入库完成 | 新增 {added} 个片段（保留历史数据）"
        else:
            added = vector_db.add_documents_full(split_docs)
            return f"✅ 全量重建完成 | 入库 {added} 个片段（已清空历史）"

    except Exception as e:
        return f"❌ 文档加载异常：{str(e)}"

def reload_all_docs_full():
    return load_all_docs(is_incremental=False)

# ====================== RAG主函数 ✅【五装饰器：兜底+重试+降级+日志+限流】 ======================
# ⚠️ 装饰器顺序已修复：global_fallback(最内层) → retry → degrade → trace_log → rate_limit(最外层)
# 这样重试可以捕获异常，兜底在最后处理所有未捕获的异常
@global_fallback
@retry_decorator(max_retries=3, delay_base=1)
@degrade_decorator
@trace_log
@rate_limit
def rag_query(question: str) -> str:
    if not question.strip():
        return "⚠️ 请输入有效问题"

    filtered_results = retriever.retrieve_filtered(question, k=CONFIG["SEARCH_K"])
    if not filtered_results:
        return "⚠️ 知识库中未找到相关高匹配内容"

    context = "\n".join([item["page_content"] for item in filtered_results])
    citation = format_citation(filtered_results)
    prompt = RAG_QA_PROMPT.format(context=context, question=question)

    raw_answer = llm.invoke(prompt).content.strip()
    final_answer = reflect_answer(question, raw_answer)
    return final_answer + citation

# ====================== 测试 ======================
def run_test():
    print("\n" + "="*50)
    print("🚀 开始自动测试 增量RAG + 自省反思 + 评分过滤 + 来源引用")
    print("="*50)

    print("\n📂 步骤1：增量加载文档到向量库")
    print(load_all_docs(is_incremental=True))

    test_questions = [
        "你好",
        "知识库里面有什么内容",
        "北京天气",
        "介绍一下公司产品",
        "你是谁",
        ""
    ]

    print("\n" + "-"*50)
    print("🔍 步骤2：开始问答测试")
    print("-"*50)

    for i, q in enumerate(test_questions, 1):
        print(f"\n📌 测试 {i}：{q if q else '【空输入】'}")
        ans = rag_query(q)
        print(f"💡 回答：{ans}")
        print("-" * 40)

    print("\n🎉 所有测试完成！系统运行正常！")

if __name__ == "__main__":
    run_test()