# utils/logger.py
"""
统一日志配置模块

功能：
- 按天文件落地
- 控制台输出
- 链路追踪 ID
- 并发安全
"""
import os
import time
import uuid
import logging
from functools import wraps
from datetime import datetime
from contextvars import ContextVar

# ====================== 日志目录配置 ======================
LOG_DIR = os.getenv("LOG_DIR", "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# ====================== 日志格式配置 ======================
LOG_FORMAT = "%(asctime)s | %(levelname)s | [%(trace_id)s] | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ====================== 创建 logger ======================
logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.propagate = False  # 防止日志传播到 root logger 导致重复输出

# 自动补全缺失的 trace_id
class TraceIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'trace_id'):
            record.trace_id = '-'
        return True

logger.addFilter(TraceIdFilter())

formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

# 文件日志（按天切割）
def _get_log_file():
    """获取当天的日志文件路径"""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"agent-{today}.log")

file_handler = logging.FileHandler(_get_log_file(), encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 控制台日志
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ====================== 使用 ContextVar 替代全局变量 ======================
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

# ====================== 同步函数链路日志装饰器 ======================
def trace_log(func):
    """同步函数链路日志装饰器"""
    @wraps(func)  # 保留原函数信息，不破坏函数结构
    def wrapper(*args, **kwargs):
        # 生成本次调用的trace_id（使用 ContextVar，并发安全）
        trace_id = gen_trace_id()
        # 记录开始时间
        start_time = time.time()
        # 打印开始日志
        logger.info(f"开始执行：{func.__name__}", extra={"trace_id": trace_id})
        
        try:
            # 执行原函数
            result = func(*args, **kwargs)
            # 计算耗时
            cost = round(time.time() - start_time, 3)
            # 打印成功日志
            logger.info(f"执行成功：{func.__name__} | 耗时：{cost}s", extra={"trace_id": trace_id})
            return result
        
        # 异常捕获
        except Exception as e:
            cost = round(time.time() - start_time, 3)
            logger.error(f"执行异常：{func.__name__} | 耗时：{cost}s | 错误：{str(e)}", extra={"trace_id": trace_id})
            # 抛出原异常，不影响业务逻辑
            raise
    return wrapper

# ====================== 异步/流式函数链路日志装饰器 ======================
def async_trace_log(func):
    """异步/流式函数链路日志装饰器
    
    注意：被装饰的函数必须是 async generator（使用 yield 返回数据）
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = gen_trace_id()
        start_time = time.time()
        logger.info(f"开始异步执行：{func.__name__}", extra={"trace_id": trace_id})
        
        try:
            # 异步流式迭代返回数据
            async for item in func(*args, **kwargs):
                yield item
            # 流式输出完成，打印成功日志
            cost = round(time.time() - start_time, 3)
            logger.info(f"异步执行成功：{func.__name__} | 耗时：{cost}s", extra={"trace_id": trace_id})
        
        # 异步异常捕获
        except Exception as e:
            cost = round(time.time() - start_time, 3)
            logger.error(f"异步执行异常：{func.__name__} | 耗时：{cost}s | 错误：{str(e)}", extra={"trace_id": trace_id})
            raise  # 重新抛出异常，避免吞掉异常
    return wrapper

# ====================== Agent 专用链路日志装饰器 ======================
def agent_trace_log(func):
    """Agent 节点专用链路日志装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        trace_id = gen_trace_id()
        start_time = time.time()
        
        logger.info(f"Agent 开始调度：{func.__name__}", extra={"trace_id": trace_id})
        try:
            result = func(*args, **kwargs)
            cost = round(time.time() - start_time, 2)
            logger.info(f"Agent 调度成功 | 耗时：{cost}s", extra={"trace_id": trace_id})
            return result
        except Exception as e:
            cost = round(time.time() - start_time, 2)
            logger.error(f"Agent 调度失败 | 耗时：{cost}s | 错误：{str(e)}", extra={"trace_id": trace_id})
            raise
    return wrapper
