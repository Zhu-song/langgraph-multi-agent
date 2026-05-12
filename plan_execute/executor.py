"""
执行器节点 (Executor)

执行单个子任务步骤，调用合适的工具完成具体工作
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from config import llm
from plan_execute.state import PlanExecuteState, StepResult, update_state_timestamp


# 工具名称映射 - 延迟导入避免循环依赖
_tool_mapping_cache = None

def get_tool_mapping():
    """获取工具名称到工具对象的映射（延迟导入）"""
    global _tool_mapping_cache
    if _tool_mapping_cache is not None:
        return _tool_mapping_cache
    
    # 延迟导入，避免循环依赖
    from tools import core_tools
    
    _tool_mapping_cache = {
        "calculator": next((t for t in core_tools if t.name == "calculator"), None),
        "web_search": next((t for t in core_tools if t.name == "web_search"), None),
        "translate": next((t for t in core_tools if t.name == "translate_text"), None),
        "summary": next((t for t in core_tools if t.name == "long_text_summary"), None),
        "file_tool": next((t for t in core_tools if t.name == "file_operate"), None),
        "json_tool": next((t for t in core_tools if t.name == "json_operate"), None),
        "text_stat": next((t for t in core_tools if t.name == "text_stat_clean"), None),
        "text_format": next((t for t in core_tools if t.name == "text_format_convert"), None),
        "time_tool": next((t for t in core_tools if t.name == "time_query"), None),
        "random_tool": next((t for t in core_tools if t.name == "random_generate"), None),
        "rag_knowledge_query": next((t for t in core_tools if t.name == "rag_knowledge_query"), None),
        "graph_knowledge_query": next((t for t in core_tools if t.name == "graph_knowledge_query"), None),
        "lightrag_operate": next((t for t in core_tools if t.name == "lightrag_operate"), None),
        "reflection_self_check": next((t for t in core_tools if t.name == "reflection_self_check"), None),
    }
    return _tool_mapping_cache


EXECUTOR_SYSTEM_PROMPT = """你是一个任务执行专家。你的职责是分析当前步骤，选择合适的工具或直接回答来完成任务。

执行原则：
1. 分析当前步骤的需求，判断是否需要调用工具
2. 如果需要工具，选择最合适的工具并构造正确的参数
3. 如果不需要工具，直接给出回答
4. 保持回答简洁、准确、完整

可用工具：
- calculator: 数学计算，参数 {"expression": "计算表达式"}
- web_search: 联网搜索，参数 {"query": "搜索关键词"}
- translate: 翻译，参数 {"text": "要翻译的文本", "target_lang": "zh/en"}
- summary: 摘要，参数 {"text": "长文本"}
- time_tool: 获取时间，参数 {}
- rag_knowledge_query: 知识库查询，参数 {"query": "查询问题"}

输出格式：
必须返回 JSON 格式：
{
    "thinking": "分析思路",
    "action": "工具名称或直接回答",
    "tool_input": {"参数名": "参数值"},  // 如果使用工具
    "direct_answer": "直接回答内容"  // 如果不使用工具
}

注意：
- action 可以是工具名称或 "direct_answer"
- 如果使用工具，必须提供 tool_input
- 如果直接回答，必须提供 direct_answer"""


def select_tool_for_step(step: str) -> tuple:
    """
    根据步骤内容选择合适的工具
    
    优先级：时间 > 计算 > 翻译 > 摘要 > 知识库 > 搜索
    注意：搜索关键词最泛，必须放最后作为兜底
    
    Args:
        step: 步骤描述
        
    Returns:
        tuple: (工具名称, 工具参数)
    """
    step_lower = step.lower()
    
    # 时间相关（优先匹配，避免被搜索抢走）
    if any(kw in step_lower for kw in ["时间", "日期", "星期", "几点", "time_tool", "今天"]):
        return "time_tool", {}
    
    # 计算相关
    if any(kw in step_lower for kw in ["计算", "算", "求", "等于", "+", "-", "*", "/", "加", "减", "乘", "除"]):
        import re
        math_pattern = r'[\d\+\-\*\/\(\)\.\s]+'
        matches = re.findall(math_pattern, step)
        if matches:
            expr = ''.join(matches).replace(' ', '')
            return "calculator", {"expr": expr}
        return "calculator", {"expr": step}
    
    # 翻译相关
    if any(kw in step_lower for kw in ["翻译", "译成", "转成英文", "转成中文"]):
        return "translate", {"text": step, "target_lang": "en" if "英文" in step else "zh"}
    
    # 摘要相关
    if any(kw in step_lower for kw in ["摘要", "总结", "概括"]):
        return "summary", {"text": step}
    
    # 知识库相关
    if any(kw in step_lower for kw in ["知识库", "文档", "资料"]):
        return "rag_knowledge_query", {"query": step}
    
    # 搜索相关（放最后，作为兜底）
    if any(kw in step_lower for kw in ["搜索", "查询", "查", "找", "获取", "最新", "新闻", "天气"]):
        return "web_search", {"query": step}
    
    # 默认使用搜索
    return "web_search", {"query": step}


def executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """
    执行器节点：执行当前步骤
    
    Args:
        state: 当前状态
        
    Returns:
        PlanExecuteState: 更新后的状态，包含执行结果
    """
    current_step = state.get("current_step")
    step_index = state.get("current_step_index", 0)
    
    if not current_step:
        print(f"[Executor] 警告：当前步骤为空")
        state["error_message"] = "当前步骤为空"
        return update_state_timestamp(state)
    
    print(f"[Executor] 执行步骤 {step_index + 1}: {current_step[:50]}...")
    
    start_time = time.time()
    tool_used = None
    success = True
    
    try:
        # 选择工具
        tool_name, tool_params = select_tool_for_step(current_step)
        tool_used = tool_name
        
        # 获取工具映射
        tool_mapping = get_tool_mapping()
        tool = tool_mapping.get(tool_name)
        
        if tool:
            print(f"[Executor] 调用工具: {tool_name}, 参数: {tool_params}")
            
            # 执行工具
            try:
                result = tool.invoke(tool_params)
                result_str = str(result) if result else "工具执行完成，无返回值"
            except Exception as e:
                print(f"[Executor] 工具执行失败: {e}")
                # 工具失败，使用 LLM 直接回答
                result_str = _llm_fallback_answer(current_step, str(e))
                tool_used = f"{tool_name}(failed)"
        else:
            print(f"[Executor] 工具未找到: {tool_name}，使用 LLM 回答")
            result_str = _llm_fallback_answer(current_step)
            tool_used = "llm_direct"
        
        duration = time.time() - start_time
        
        # 创建步骤结果
        step_result = StepResult(
            step=current_step,
            result=result_str,
            tool_used=tool_used,
            success=success,
            duration=duration,
            timestamp=datetime.now().isoformat()
        )
        
        # 更新状态
        state["step_results"].append(step_result)
        state["current_step_index"] = step_index + 1
        
        # 更新下一步
        if step_index + 1 < len(state["plan"]):
            state["current_step"] = state["plan"][step_index + 1]
        else:
            state["current_step"] = None
            state["is_complete"] = True
        
        print(f"[Executor] 步骤 {step_index + 1} 完成，耗时 {duration:.2f}s")
        print(f"[Executor] 结果: {result_str[:100]}...")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"[Executor] 执行失败: {e}")
        
        # 创建失败的步骤结果
        step_result = StepResult(
            step=current_step,
            result=f"执行失败: {str(e)}",
            tool_used=tool_used or "unknown",
            success=False,
            duration=duration,
            timestamp=datetime.now().isoformat()
        )
        
        state["step_results"].append(step_result)
        state["error_message"] = str(e)
    
    return update_state_timestamp(state)


def _llm_fallback_answer(step: str, error_context: str = "") -> str:
    """
    使用 LLM 直接回答（工具失败时的 fallback）
    
    Args:
        step: 步骤描述
        error_context: 错误上下文
        
    Returns:
        str: LLM 的回答
    """
    try:
        prompt = f"请完成以下任务：{step}"
        if error_context:
            prompt += f"\n\n注意：之前的工具调用失败了（{error_context}），请直接回答。"
        
        messages = [
            SystemMessage(content="你是一个 helpful 的助手，请直接回答用户的问题。"),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"无法完成任务: {step}。错误: {e}"


def should_continue(state: PlanExecuteState) -> str:
    """
    判断工作流是否继续
    
    Args:
        state: 当前状态
        
    Returns:
        str: "continue" 继续执行, "replan" 需要重规划, "end" 结束
    """
    # 检查是否需要重规划
    if state.get("should_replan", False):
        # 检查重规划次数
        if state.get("replan_count", 0) >= 3:
            print("[Router] 重规划次数过多，直接结束")
            return "end"
        return "replan"
    
    # 检查是否完成
    if state.get("is_complete", False):
        return "end"
    
    # 检查是否还有步骤
    current_index = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    
    if current_index >= len(plan):
        return "end"
    
    # 检查最后一步是否失败
    step_results = state.get("step_results", [])
    if step_results and not step_results[-1].get("success", True):
        # 如果最后一步失败，考虑重规划（返回 "replan" 让 replanner 节点处理状态修改）
        if state.get("replan_count", 0) < 3:
            return "replan"
    
    return "continue"


def generate_final_response(state: PlanExecuteState) -> PlanExecuteState:
    """
    生成最终回答
    
    综合所有步骤的执行结果，生成完整的最终回答
    
    Args:
        state: 当前状态
        
    Returns:
        PlanExecuteState: 包含最终回答的状态
    """
    print("[Finalizer] 生成最终回答...")
    
    step_results = state.get("step_results", [])
    original_input = state.get("input", "")
    
    if not step_results:
        state["final_response"] = "未能完成任何步骤。"
        return update_state_timestamp(state)
    
    # 构建执行摘要
    execution_summary = []
    for i, result in enumerate(step_results, 1):
        step_desc = result.get("step", f"步骤{i}")
        step_result = result.get("result", "")
        tool = result.get("tool_used", "")
        success = "✓" if result.get("success", True) else "✗"
        execution_summary.append(f"{success} 步骤{i}: {step_desc}\n  结果: {step_result[:200]}...")
    
    summary_text = "\n\n".join(execution_summary)
    
    try:
        # 使用 LLM 生成最终回答
        prompt = f"""基于以下任务执行过程，生成一个完整的最终回答。

原始任务: {original_input}

执行过程:
{summary_text}

请综合以上信息，给出一个完整、清晰、有用的最终回答。回答应该：
1. 直接回应原始任务
2. 整合各步骤的执行结果
3. 结构清晰，易于理解
4. 如果某些步骤失败，说明影响并提供替代信息

最终回答:"""
        
        messages = [
            SystemMessage(content="你是一个专业的回答整合专家。"),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        final_answer = response.content.strip()
        
        state["final_response"] = final_answer
        print(f"[Finalizer] 最终回答生成完成，长度: {len(final_answer)}")
        
    except Exception as e:
        print(f"[Finalizer] 生成最终回答失败: {e}")
        # Fallback：简单拼接
        fallback_answer = f"任务执行完成。\n\n执行摘要:\n{summary_text}"
        state["final_response"] = fallback_answer
    
    return update_state_timestamp(state)
