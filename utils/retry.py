# utils/retry.py
import asyncio
import time
from functools import wraps

# 全局配置：最多重试3次，基础等待1秒（指数退避）
MAX_RETRY = 3
BASE_DELAY = 1.0  # 秒


def with_retry(func=None, max_retry=MAX_RETRY, base_delay=BASE_DELAY):
    """通用同步重试装饰器
    功能：
    1. 捕获函数异常自动重试
    2. 支持RAG空召回判定（未找到/无相关 自动重试）
    3. 指数退避重试（等待时间越来越长）
    """
    def decorator(f):
        @wraps(f)  # 保留原函数名称、文档字符串，便于调试
        def wrapper(*args, **kwargs):
            last_err = None  # 记录最后一次异常信息
            # 循环执行：第1次到最大重试次数
            for attempt in range(1, max_retry + 1):
                try:
                    # 执行目标函数
                    result = f(*args, **kwargs)

                    # ======================
                    # RAG 专用：空召回重试
                    # 如果返回字符串且包含“未找到/无相关”，判定为空结果，强制重试
                    # ======================
                    if isinstance(result, str) and (
                        "未找到相关" in result 
                        or "暂无相关" in result 
                        or "无相关" in result
                    ):
                        raise ValueError(f"[空召回] 检索结果为空 | attempt={attempt}")

                    # 执行成功 & 非空召回 → 返回结果
                    return result

                except Exception as e:
                    last_err = e  # 保存异常
                    # 打印失败日志（方便排查问题）
                    msg = f"【失败】attempt={attempt} | func={f.__name__} | err={str(e)} | args={args} | kwargs={kwargs}"
                    print(msg)

                    # 达到最大重试次数 → 不再重试
                    if attempt >= max_retry:
                        break

                    # ======================
                    # 指数退避算法：等待时间 = 1s → 2s → 4s
                    # ======================
                    wait = base_delay * (2 ** (attempt - 1))
                    print(f"⏳ {wait}s 后重试...\n")
                    time.sleep(wait)  # 同步等待

            # 所有重试都失败 → 抛出最后一次异常
            raise last_err
        return wrapper

    # 支持 @with_retry 或 @with_retry(max_retry=5)
    if func:
        return decorator(func)
    return decorator


def async_with_retry(func=None, max_retry=MAX_RETRY, base_delay=BASE_DELAY):
    """通用异步重试装饰器（专门适配流式/llm.astream）
    作用：给异步生成器、异步函数做自动重试
    ⚠️ 已修复：不再丢失第一个chunk
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_retry + 1):
                try:
                    # 执行异步函数/生成器
                    result = f(*args, **kwargs)

                    # ======================
                    # 异步生成器特殊处理（已修复chunk丢失问题）：
                    # 创建一个包装生成器，先yield第一个chunk，再yield剩余内容
                    # ======================
                    async def safe_generator():
                        gen = result.__aiter__()
                        first_chunk = await gen.__anext__()
                        yield first_chunk  # 先yield第一个chunk
                        async for chunk in gen:  # 再yield剩余内容
                            yield chunk
                    
                    return safe_generator()

                except Exception as e:
                    last_err = e
                    # 异步失败日志
                    msg = f"【异步失败】attempt={attempt} | func={f.__name__} | err={str(e)}"
                    print(msg)

                    if attempt >= max_retry:
                        break

                    # 异步指数退避
                    wait = base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(wait)

            # 重试耗尽，抛出最终异常
            raise last_err
        return wrapper

    if func:
        return decorator(func)
    return decorator