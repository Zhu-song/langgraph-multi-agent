# utils/rate_limit.py
import time
from functools import wraps

# 内存存储：用户ID -> 最后请求时间戳
# 用于记录每个用户上一次调用接口的时间
REQUEST_RECORD = {}
# 限流配置：1秒内最多允许1次请求
LIMIT_SECONDS = 1

def rate_limit(func):
    """
    全局请求限流装饰器（同步接口用）
    功能：同一用户（session_id）1秒内只能调用1次接口
    作用：防止接口被刷、减轻大模型/服务器压力
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 默认使用通用用户ID（未传入session_id时）
        session_id = "default_user"
        # 如果有参数，默认取第一个参数作为 session_id（截断20位）
        if args:
            session_id = str(args[0])[:20]

        # 获取当前时间戳
        now = time.time()
        # 获取该用户上一次请求的时间
        last_time = REQUEST_RECORD.get(session_id, 0)

        # 判断：当前时间 - 上次时间 < 限流间隔 → 触发限流
        if now - last_time < LIMIT_SECONDS:
            return {"code": 429, "message": "⚠️ 请求过于频繁，请1秒后再试"}

        # 没有触发限流：更新最后请求时间
        REQUEST_RECORD[session_id] = now
        # 执行原函数
        return func(*args, **kwargs)
    return wrapper

def async_rate_limit(func):
    """
    异步限流装饰器（给 SSE 流式接口 / 异步生成器用）
    功能和同步版一致，只是适配异步流式输出格式
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 识别用户 session_id
        session_id = "default_user"
        if args:
            session_id = str(args[0])[:20]

        now = time.time()
        last_time = REQUEST_RECORD.get(session_id, 0)

        # 触发限流：直接返回提示语并结束流式输出
        if now - last_time < LIMIT_SECONDS:
            yield "⚠️ 请求过于频繁，请1秒后再试"
            return

        # 更新请求时间
        REQUEST_RECORD[session_id] = now

        # 正常执行异步函数
        async for item in func(*args, **kwargs):
            yield item
    return wrapper