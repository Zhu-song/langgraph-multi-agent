#================== 智能调度中枢（Supervisor Agent）==================
# 功能：根据用户问题自动分类 → 路由到对应工具
# 输出：唯一路由标签（calc/time/translate/summary/search/file/direct）

from config import llm
from graph.state import AgentState

def supervisor_agent(state: AgentState) -> dict:
    """
    调度中枢 Supervisor
    根据用户问题判断路由，输出唯一标识：
    calc        -> 数学计算
    time        -> 时间日期
    translate   -> 中英翻译
    summary     -> 长文本摘要
    search      -> 联网搜索
    file        -> 文件操作
    json        ->JSON格式化/校验
    text_stat   ->文本统计清洗
    text_format ->大小写/驼峰下划线转换
    random      ->随机数字/密码/抽签
    rag         -> 私有文档知识库问答
    graphrag    -> 知识图谱实体关系/多跳推理问答
    reflection  -> 答案自省纠错、逻辑校验、优化润色
    direct      -> 大模型直接回答，无需工具
    """
    # 从状态中获取用户问题
    question = state["question"]
    
    # ===================== 【仅新增：读取对话历史】 =====================
    chat_history = state.get("chat_history", "")  # 不破坏原有代码
    # =================================================================

    # ===================== 【新增：全局上下文合并 → 所有工具自动生效】 =====================
    if chat_history.strip():
        # 把上下文拼进问题，所有 worker 自动读到，不用改任何工具代码
        question = f"对话历史：{chat_history}\n当前用户问题：{question}"
        state["question"] = question  # 覆盖到状态，全局生效
    # ====================================================================================

    # 调度提示词：严格分类、严格输出单个关键词
    prompt = f"""
你是任务分类调度器，只允许严格输出下面其中一个单词，不要解释、不要多余文字：
可选择标识：calc、time、translate、summary、search、file、json、text_stat、text_format、random、rag、graphrag、reflection、direct

规则：
1. 数学计算、表达式运算 → 输出 calc
2. 查时间、日期、星期、日期间隔 → 输出 time
3. 中英文互译、专业文本翻译 → 输出 translate
4. 给长文本、文章、段落摘要总结 → 输出 summary
5. 需要查最新资讯、技术文档、实时信息 → 输出 search
6. 新建文件夹、创建/读取/追加文件 → 输出 file
7.JSON格式化、美化、校验JSON格式 → 输出 json
8.文本字数统计、清理多余空格换行 → 输出 text_stat
9.字符串大小写、驼峰下划线互转 → 输出 text_format
10.生成随机数字、密码、抽签 → 输出 random
11.查询本地私有文档、内部资料、知识库问答 → 输出 rag
12.查询实体关系、架构关联、多跳推理 → 输出 graphrag
13.答案纠错、逻辑校验、自省优化、润色整理 → 输出 reflection
14.其他日常闲聊 → 输出 direct

用户问题：{question}
"""
    # 调用大模型进行路由判断
    res = llm.invoke(prompt)
    # 清理结果，统一小写，避免格式错误
    route = res.content.strip().lower()
    
    # 把路由结果回填到状态
    return {"route": route}


# ====================== 本地测试 ======================
if __name__ == "__main__":
    print("🧪 测试调度中枢（Supervisor）...\n")

    # 测试用例列表（全覆盖 11 种路由）
    test_cases = [
        {"question": "123+456等于多少？"},
        {"question": "今天几号？"},
        {"question": "把‘你好’翻译成英文"},
        {"question": "帮我总结这篇文章：人工智能..."},
        {"question": "2026大模型最新技术"},
        {"question": "帮我创建一个文件夹test"},
        {"question": '格式化这个JSON：{"name":"张三","age":20}'},
        {"question": "统计字数：我   爱   编程   今天  天气  真好"},
        {"question": "userName转下划线格式"},
        {"question": "帮我生成一个8位随机密码"},
        {"question": "帮我检查优化这个答案"},
        {"question": "你好呀，今天天气怎么样"}
    ]

    # 批量测试
    for i, case in enumerate(test_cases):
        result = supervisor_agent(case)
        print(f"{i}. 问题：{case['question']}")
        print(f"   → 路由结果：{result['route']}\n")

    print("🎉 调度中枢测试完成！")