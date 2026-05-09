# utils/logger.py
import time
import uuid
import logging
from functools import wraps
from datetime import datetime
from contextvars import ContextVar

# 配置日志格式（全局统一）
# 输出格式：时间 | 级别 | 内容
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ====================== ⚠️ 使用 ContextVar 替代全局变量 ======================
# ContextVar 是 Python 3.7+ 提供的上下文变量，支持并发安全
# 每个异步任务/线程都有独立的 trace_id，不会互相覆盖
_trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')

def gen_trace_id() -> str:
    """生成唯一链路追踪ID（8位UUID）
    作用：给每一次请求分配一个ID，方便日志追踪
    
    ⚠️ 已修复：使用 ContextVar 确保并发安全
    """
    trace_id = str(uuid.uuid4())[:8]
    _trace_id_var.set(trace_id)
    return trace_id

def get_trace_id() -> str:
    """获取当前链路ID
    如果没有则自动生成一个
    """
    trace_id = _trace_id_var.get()
    return trace_id if trace_id else gen_trace_id()

# 同步函数链路日志装饰器
def trace_log(func):
    @wraps(func)  # 保留原函数信息，不破坏函数结构
    def wrapper(*args, **kwargs):
        # 生成本次调用的trace_id（使用 ContextVar，并发安全）
        trace_id = gen_trace_id()
        # 记录开始时间
        start_time = time.time()
        # 打印开始日志
        logger.info(f"【{trace_id}】开始执行：{func.__name__}")
        
        try:
            # 执行原函数
            result = func(*args, **kwargs)
            # 计算耗时
            cost = round(time.time() - start_time, 3)
            # 打印成功日志
            logger.info(f"【{trace_id}】执行成功：{func.__name__} | 耗时：{cost}s")
            return result
        
        # 异常捕获
        except Exception as e:
            cost = round(time.time() - start_time, 3)
            logger.error(f"【{trace_id}】执行异常：{func.__name__} | 耗时：{cost}s | 错误：{str(e)}")
            # 抛出原异常，不影响业务逻辑
            raise
    return wrapper

# 异步/流式函数链路日志装饰器
def async_trace_log(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = gen_trace_id()
        start_time = time.time()
        logger.info(f"【{trace_id}】开始异步执行：{func.__name__}")
        
        try:
            # 异步流式迭代返回数据
            async for item in func(*args, **kwargs):
                yield item
            # 流式输出完成，打印成功日志
            cost = round(time.time() - start_time, 3)
            logger.info(f"【{trace_id}】异步执行成功：{func.__name__} | 耗时：{cost}s")
        
        # 异步异常捕获
        except Exception as e:
            cost = round(time.time() - start_time, 3)
            logger.error(f"【{trace_id}】异步执行异常：{func.__name__} | 耗时：{cost}s | 错误：{str(e)}")
            raise  # ⚠️ 已修复：重新抛出异常，避免吞掉异常
    return wrapper