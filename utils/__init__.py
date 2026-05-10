# utils 模块 - 工具函数集合
"""
项目通用工具函数模块

包含:
- logger: 日志配置和装饰器
- retry: 重试装饰器 (with_retry, async_with_retry)
- rate_limit: 限流装饰器
- global_fallback: 全局兜底装饰器 (global_fallback_decorator, async_global_fallback_decorator)
- degrade_strategy: 降级策略装饰器 (degrade_wrapper, async_degrade_wrapper)
"""

from .logger import logger, trace_log, async_trace_log, agent_trace_log
from .retry import with_retry, async_with_retry
from .rate_limit import rate_limit
from .global_fallback import global_fallback_decorator, async_global_fallback_decorator
from .degrade_strategy import degrade_wrapper, async_degrade_wrapper

__all__ = [
    "logger",
    "trace_log",
    "async_trace_log",
    "agent_trace_log",
    "with_retry",
    "async_with_retry",
    "rate_limit",
    "global_fallback_decorator",
    "async_global_fallback_decorator",
    "degrade_wrapper",
    "async_degrade_wrapper",
]
