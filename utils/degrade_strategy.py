# utils/degrade_strategy.py
from functools import wraps

# 降级文案统一配置（全局管理，便于修改）
# 作用：系统出现异常时，告知用户当前降级模式，提升体验
DEGRADE_MSG = {
    "level1": "🌐 联网搜索异常，已切换为【本地知识库】模式作答",  # 一级降级：联网不可用，用本地RAG
    "level2": "📚 未检索到相关专业文档，将基于通用常识回答",    # 二级降级：RAG无结果，用LLM常识回答
    "level3": "⚙️ 智能调度异常，已降级为【极简单轮问答】模式"   # 三级降级：Agent崩溃，用最简模式
}

# 标记开关：控制各级降级是否触发（全局可修改，实现动态降级）
# 各标记对应不同异常场景，通过set_degrade_flag函数控制开关
DEGRADE_FLAG = {
    "search_failed": False,  # 标记：联网搜索是否失败（触发一级降级）
    "rag_empty": False,      # 标记：RAG检索是否为空（触发二级降级）
    "agent_error": False     # 标记：Agent调度是否异常（触发三级降级）
}

def set_degrade_flag(flag_name: str, value: bool):
    """设置降级标记（对外提供的控制接口）
    :param flag_name: 标记名称（必须是DEGRADE_FLAG中的key）
    :param value: 标记值（True=触发降级，False=取消降级）
    """
    if flag_name in DEGRADE_FLAG:
        DEGRADE_FLAG[flag_name] = value

def check_level1_degrade() -> bool:
    """一级降级校验：判断是否触发一级降级（联网搜索失败）"""
    return DEGRADE_FLAG["search_failed"]

def check_level2_degrade() -> bool:
    """二级降级校验：判断是否触发二级降级（RAG召回失败）"""
    return DEGRADE_FLAG["rag_empty"]

def check_level3_degrade() -> bool:
    """三级降级校验：判断是否触发三级降级（Agent调度异常）"""
    return DEGRADE_FLAG["agent_error"]

# 同步函数降级装饰器（适配普通同步函数，如rag_query、graph_qa）
def degrade_wrapper(func):
    @wraps(func)  # 保留原函数名称、文档信息，不破坏函数结构
    def wrapper(*args, **kwargs):
        # 降级优先级：三级 > 二级 > 一级（异常越严重，降级级别越高）
        # 三级降级（最高优先级）：Agent调度异常，直接返回降级提示，不执行原函数
        if check_level3_degrade():
            return DEGRADE_MSG["level3"] + "\n请直接提问，将为你极简作答"
        # 二级降级：RAG无结果，先返回降级提示，再执行原函数（用常识回答）
        if check_level2_degrade():
            return DEGRADE_MSG["level2"] + "\n" + func(*args, **kwargs)
        # 一级降级：联网失败，先返回降级提示，再执行原函数（用本地知识库回答）
        if check_level1_degrade():
            return DEGRADE_MSG["level1"] + "\n" + func(*args, **kwargs)
        # 无任何降级，正常执行原函数
        return func(*args, **kwargs)
    return wrapper

# 异步流式降级装饰器（适配异步流式函数，如rag_stream_generator、SSE接口）
def async_degrade_wrapper(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 三级降级：直接返回降级提示，终止流式输出
        if check_level3_degrade():
            yield DEGRADE_MSG["level3"]
            return
        # 二级/一级降级：先返回降级提示，再继续执行流式函数
        if check_level2_degrade():
            yield DEGRADE_MSG["level2"]
        if check_level1_degrade():
            yield DEGRADE_MSG["level1"]
        # 无降级/已返回降级提示，正常流式输出原函数内容
        async for item in func(*args, **kwargs):
            yield item
    return wrapper