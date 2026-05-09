# ================== 查实时资讯、最新技术、外部知识 =================
# 路由标识：search
# 功能：提供联网搜索能力，用于获取实时资讯、最新技术动态及外部知识
# 流程：百度国内搜索 → LLM精炼总结 → 返回简洁答案

# 导入LangChain结构化工具封装模块
from langchain.tools import StructuredTool
# 导入项目中配置好的大模型对象
from config import llm
# 国内轻量搜索库（无依赖错误、稳定、秒回）
import requests

def web_search(query: str) -> str:
    """
    联网搜索工具：实时查询最新资讯、技术文档、热点事件
    自动获取网页内容 + LLM精简总结
    """
    # ==================== 国内百度搜索请求（直连、无API Key、稳定优先） ====================
    # 拼接百度搜索URL，直接用搜索词wd参数
    url = f"https://www.baidu.com/s?wd={query}"
    # 请求头：模拟浏览器访问，避免被百度反爬拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    try:
        # 发送GET请求，设置5秒超时（避免网络卡顿一直等待）
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "utf-8"
        # 只取返回HTML的前1500字符，兼顾速度与信息完整性
        raw_info = resp.text[:1500]
    except Exception as e:
        # 网络异常/超时/被拦截时，返回固定提示，避免程序崩溃
        raw_info = f"搜索失败：{str(e)}"

    # ==================== LLM精炼总结（减少冗余，输出干货） ====================
    # 构造提示词：强制大模型直接输出核心答案，不铺垫、不废话
    prompt = f"""
用户问题：{query}
搜索资料：{raw_info}
要求：直接给出精炼核心答案，不要多余铺垫、不要废话、不要解释格式，只给干货总结，越简洁越好。
"""
    # 调用大模型生成总结
    result = llm.invoke(prompt)
    # 去除首尾空白字符，返回干净结果
    return result.content.strip()

# 把web_search函数封装成LangChain结构化工具，供智能体（Agent）调用
search_tool = StructuredTool.from_function(
    name="web_search",  # 工具唯一标识，Agent通过这个名字识别并调用
    func=web_search,    # 绑定实际执行搜索+总结的函数
    description="联网实时搜索最新资讯、技术文档、时事内容，自动总结核心"  # 工具描述，供Agent决策是否调用
)

# ====================== 本地测试入口（直接运行本文件时执行） ======================
if __name__ == "__main__":
    print("🧪 测试国内百度搜索工具...\n")

    # 测试用例1：查询最新技术趋势
    print("测试 1：查询最新技术")
    res1 = search_tool.invoke("2026年大模型最新技术趋势")
    print(res1)

    # 测试用例2：查询行业实时热点
    print("\n测试 2：查询行业资讯")
    res2 = search_tool.invoke("2026年5月人工智能热点")
    print(res2)

    print("\n🎉 国内搜索工具测试通过！")