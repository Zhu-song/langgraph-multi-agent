# rag/rag_stream.py
import asyncio
import time
from functools import wraps
from rag.rag_core import retriever, llm, reflect_answer, format_citation
from rag.citation import format_citation

# 🔥【新增 1】引入统一规范提示词
from prompts.system_prompt import RAG_QA_PROMPT

# ✅ 【正确规范：从全局兜底包导入】
from utils.global_fallback import async_global_fallback_decorator

# ====================== ✅ 【异步限流 + 防重复请求】 ======================
ASYNC_REQUEST_CACHE = {}
LIMIT_SECONDS = 1  # 1秒只能请求1次

def async_rate_limit(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not args:
            async for item in func(*args, **kwargs):
                yield item
            return
        
        key = str(args[0])
        now = time.time()

        # 限流判断
        if key in ASYNC_REQUEST_CACHE and now - ASYNC_REQUEST_CACHE[key] < LIMIT_SECONDS:
            yield "⚠️ 请求过于频繁，请1秒后再试"
            return

        ASYNC_REQUEST_CACHE[key] = now
        async for item in func(*args, **kwargs):
            yield item
    return wrapper

# ====================== ✅ 【异步链路日志：直接嵌入】 ======================
import uuid
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def async_trace_log(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        logger.info(f"[{trace_id}] 开始流式执行：rag_stream_generator | 问题：{args[0]}")
        
        try:
            async for item in func(*args, **kwargs):
                yield item
            cost = round(time.time() - start_time, 2)
            logger.info(f"[{trace_id}] 流式执行成功 | 耗时：{cost}s")
        except Exception as e:
            cost = round(time.time() - start_time, 2)
            logger.error(f"[{trace_id}] 流式执行失败 | 耗时：{cost}s | 错误：{str(e)}")
            raise
    return wrapper

# ==========================
# ✅ 异步三级故障降级（直接嵌入，不动原有代码）
# ==========================
def async_degrade_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 先输出降级提示（自动识别）
            async for item in func(*args, **kwargs):
                if "未找到相关" in str(item):
                    yield "📚 未找到知识库内容，已降级 → 通用常识回答\n"
                elif "搜索" in str(item) and ("失败" in str(item) or "超时" in str(item)):
                    yield "🌐 联网不可用，已降级 → 仅本地知识库回答\n"
                yield item
        except Exception:
            yield "⚙️ 系统调度异常，已降级 → 极简问答模式\n"
    return wrapper

# ==========================
# ✅ 直接嵌入异步重试装饰器（不影响任何原有代码）
# ==========================
def async_retry_decorator(max_retries=3, delay_base=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    # 直接运行原函数，完全不改逻辑
                    async for value in func(*args, **kwargs):
                        yield value
                    return
                except Exception as e:
                    last_err = f"❌ 错误：{str(e)}"
                    print(f"🔁 流式重试 {attempt}/{max_retries} | 原因：{str(e)}")
                    if attempt >= max_retries:
                        break
                    await asyncio.sleep(delay_base * attempt)
            yield last_err
        return wrapper
    return decorator

# ==========================
# 原有函数完全不动 ✅
# 最顶部增加 @async_rate_limit
# ==========================
@async_rate_limit
@async_trace_log
@async_degrade_decorator
@async_global_fallback_decorator  # ✅ 真正使用全局兜底包
@async_retry_decorator(max_retries=3, delay_base=1)
async def rag_stream_generator(question: str):
    """
    RAG 流式生成器：逐字返回回答 + 来源引用
    作用：给 FastAPI SSE 流式接口使用，实现打字机效果输出
    """
    # 空内容判断
    if not question.strip():
        yield "⚠️ 请输入有效问题"
        return

    try:
        # 1. 向量库检索 + 相似度分数过滤（只保留高置信度片段）
        filtered = retriever.retrieve_filtered(question)
        # 无结果直接返回提示
        if not filtered:
            yield "⚠️ 知识库中未找到相关内容"
            return

        # 2. 拼接检索到的文档片段，生成给大模型的提示词
        context = "\n".join([item["page_content"] for item in filtered])
        
        # 🔥【改造 2】使用统一规范提示词（只改这一行！）
        prompt = RAG_QA_PROMPT.format(context=context, question=question)

        # 3. 异步流式调用大模型，逐字输出内容
        async for chunk in llm.astream(prompt):
            content = chunk.content
            if content:
                yield content

        # 4. 大模型输出完成后，追加来源引用信息
        citation = format_citation(filtered)
        if citation:
            yield citation

    # 异常处理：报错时直接返回错误信息
    except Exception as e:
        yield f"❌ 错误：{str(e)}"
