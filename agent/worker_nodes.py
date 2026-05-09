# ================== 多智能体工具执行节点（Worker）==================
# 功能：根据路由调度，执行对应工具（计算/时间/翻译/摘要/搜索/文件）
# 每个节点独立负责一种工具，执行后返回结果存入状态

from graph.state import AgentState
from tools import (
    calc_tool,
    time_tool,
    translate_tool,
    summary_tool,
    search_tool,
    file_tool,
    
    json_tool,
    text_stat_tool,
    text_format_tool,
    random_tool,
    rag_tool,
    graphrag_tool,
    reflection_tool
)

# ------------------------------
# 计算器节点
# ------------------------------
def calc_worker(state: AgentState) -> dict:
    question = state["question"]
    result = calc_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 时间日期节点
# ------------------------------
def time_worker(state: AgentState) -> dict:
    question = state["question"]
    result = time_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 翻译节点
# ------------------------------
def translate_worker(state: AgentState) -> dict:
    question = state["question"]
    result = translate_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 摘要节点
# ------------------------------
def summary_worker(state: AgentState) -> dict:
    question = state["question"]
    result = summary_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 联网搜索节点
# ------------------------------
def search_worker(state: AgentState) -> dict:
    question = state["question"]
    result = search_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 文件操作节点
# ------------------------------
def file_worker(state: AgentState) -> dict:
    question = state["question"]
    result = file_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# JSON处理节点
# ------------------------------
def json_worker(state: AgentState) -> dict:
    question = state["question"]
    result = json_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 文本统计清洗节点
# ------------------------------
def text_stat_worker(state: AgentState) -> dict:
    question = state["question"]
    result = text_stat_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 文本格式转换节点
# ------------------------------
def text_format_worker(state: AgentState) -> dict:
    question = state["question"]
    result = text_format_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# 随机生成节点
# ------------------------------
def random_worker(state: AgentState) -> dict:
    question = state["question"]
    result = random_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# RAG私有知识库问答节点
# ------------------------------
def rag_worker(state: AgentState) -> dict:
    question = state["question"]
    result = rag_tool.run(question)
    return {"tool_result": result, "final_answer": result}


# ------------------------------
# 知识图谱GraphRAG推理节点
# ------------------------------
def graphrag_worker(state: AgentState) -> dict:
    question = state["question"]
    result = graphrag_tool.run(question)
    return {"tool_result": result, "final_answer": result}

# ------------------------------
# Reflection自省纠错节点
# ------------------------------
def reflection_worker(state: AgentState) -> dict:
    question = state["question"]
    result = reflection_tool.run(question)
    return {"tool_result": result, "final_answer": result}



# ====================== 本地测试 ======================
if __name__ == "__main__":
    print("🧪 测试所有工具执行节点...\n")

    # 测试计算器
    res = calc_worker({"question": "1+1等于几"})
    print("计算器结果：", res["final_answer"])

    # 测试时间
    res = time_worker({"question": "现在几点"})
    print("时间结果：", res["final_answer"])

    # 测试翻译
    res = translate_worker({"question": "翻译你好"})
    print("翻译结果：", res["final_answer"])

    # 测试JSON处理
    res = json_worker({"question": '{"name":"张三","age":20,"city":"北京"}'})
    print("JSON处理结果：", res["final_answer"])

    # 测试文本统计清洗
    res = text_stat_worker({"question": "我   爱   编程   \n 今天  天气  真好"})
    print("文本清洗结果：", res["final_answer"])

    # 测试文本格式转换
    res = text_format_worker({"question": "userNameLangGraph"})
    print("文本格式转换结果：", res["final_answer"])

    # 测试随机生成
    res = random_worker({"question": "pwd"})
    print("随机密码结果：", res["final_answer"])

    res = random_worker({"question": "choice,苹果,香蕉,橘子"})
    print("随机选择结果：", res["final_answer"])

    print("\n🎉 所有工具节点测试完成！")