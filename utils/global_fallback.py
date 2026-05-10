# utils/global_fallback.py
from functools import wraps
from langchain_core.messages import AIMessage

# 全局友好兜底文案映射
# 作用：系统出现各种异常时，给用户返回友好提示，不暴露技术报错
FALLBACK_MSG = {
    "api_timeout": "⚠️ 大模型接口请求超时，请稍后再试",
    "auth_fail": "⚠️ 接口鉴权失败，请检查API Key配置",
    "empty_rag": "⚠️ 知识库暂无相关内容，无法解答",
    "empty_search": "⚠️ 联网搜索未找到相关结果",
    "file_error": "⚠️ 文件读取失败或格式不支持，请检查文档",
    "param_error": "⚠️ 工具参数解析错误，请检查指令格式",
    "network_error": "⚠️ 网络异常，请检查网络连接",
    "default": "⚠️ 系统暂时出现异常，请稍后重试"
}

def global_fallback_decorator(func):
    """全局故障兜底装饰器：捕获所有异常，返回友好文案（LangGraph 兼容格式）"""
    @wraps(func)  # 保留原函数信息，不破坏函数结构
    def wrapper(*args, **kwargs):
        try:
            # 正常执行原函数
            return func(*args, **kwargs)
        except Exception as e:
            # 捕获所有异常，转为小写方便匹配
            err = str(e).lower()
            
            # 根据异常关键词匹配友好提示
            msg = FALLBACK_MSG["default"]  # 默认兜底
            if "timeout" in err or "超时" in err:
                msg = FALLBACK_MSG["api_timeout"]
            elif "auth" in err or "key" in err or "鉴权" in err:
                msg = FALLBACK_MSG["auth_fail"]
            elif "file" in err or "pdf" in err or "编码" in err:
                msg = FALLBACK_MSG["file_error"]
            elif "param" in err or "参数" in err:
                msg = FALLBACK_MSG["param_error"]
            elif "network" in err or "连接" in err:
                msg = FALLBACK_MSG["network_error"]
            
            # 返回 LangGraph 兼容格式（dict 包含 messages）
            return {"messages": [AIMessage(content=msg)]}
    return wrapper


def async_global_fallback_decorator(func):
    """异步版全局兜底（适配流式输出、astream、SSE）"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 异步流式逐字返回内容
            async for item in func(*args, **kwargs):
                yield item
        except Exception as e:
            # 捕获异步/流式中的异常
            err = str(e).lower()
            if "timeout" in err or "超时" in err:
                yield FALLBACK_MSG["api_timeout"]
            elif "auth" in err or "key" in err:
                yield FALLBACK_MSG["auth_fail"]
            elif "file" in err:
                yield FALLBACK_MSG["file_error"]
            elif "param" in err:
                yield FALLBACK_MSG["param_error"]
            else:
                yield FALLBACK_MSG["default"]
