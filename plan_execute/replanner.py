"""
重规划器节点 (Replaner)

根据执行结果和当前状态，动态调整任务计划
"""

import json
import time
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from config import llm
from plan_execute.state import PlanExecuteState, update_state_timestamp


REPLANNER_SYSTEM_PROMPT = """你是一个任务重规划专家。当任务执行过程中出现问题或需要调整时，你的职责是重新制定执行计划。

重规划触发场景：
1. 某一步骤执行失败，需要替代方案
2. 执行过程中发现原计划遗漏了重要步骤
3. 执行结果与预期不符，需要调整后续步骤
4. 用户输入发生变化，需要相应调整

重规划原则：
1. 保留已成功执行的步骤结果
2. 针对失败或问题步骤，提供替代方案
3. 保持计划的整体连贯性
4. 新计划应该更具体、更可执行

输出格式要求：
必须返回 JSON 格式：
{
    "analysis": "当前执行情况分析",
    "adjustment_reason": "调整原因",
    "new_steps": ["新步骤1", "新步骤2"],
    "keep_previous_results": true,
    "starting_from_step": 2
}

注意：
- new_steps 是完整的更新后计划（不是仅新增步骤）
- starting_from_step 表示从第几步开始重新执行（从1开始计数）
- keep_previous_results 表示是否保留之前步骤的执行结果"""


def replanner_node(state: PlanExecuteState) -> PlanExecuteState:
    """
    重规划器节点：根据执行情况调整计划
    
    Args:
        state: 当前状态
        
    Returns:
        PlanExecuteState: 更新后的状态，包含调整后的计划
    """
    print(f"[Replaner] 开始重规划...")
    
    # 增加重规划计数
    current_count = state.get("replan_count", 0)
    state["replan_count"] = current_count + 1
    
    # 检查重规划次数
    if current_count >= 3:
        print(f"[Replaner] 警告：重规划次数已达上限({current_count})，停止重规划")
        state["should_replan"] = False
        state["is_complete"] = True
        state["final_response"] = "任务执行多次尝试后仍未成功，请检查任务描述或稍后重试。"
        return update_state_timestamp(state)
    
    # 构建上下文信息
    context = _build_replan_context(state)
    
    try:
        # 调用 LLM 进行重规划
        messages = [
            SystemMessage(content=REPLANNER_SYSTEM_PROMPT),
            HumanMessage(content=context)
        ]
        
        start_time = time.time()
        response = llm.invoke(messages)
        elapsed = time.time() - start_time
        
        # 解析 JSON 响应
        content = response.content.strip()
        
        # 处理可能的 markdown 代码块
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # 解析 JSON
        replan_data = json.loads(content)
        
        new_steps = replan_data.get("new_steps", [])
        starting_from = replan_data.get("starting_from_step", 1)
        keep_previous = replan_data.get("keep_previous_results", True)
        adjustment_reason = replan_data.get("adjustment_reason", "")
        
        # 验证新计划
        if not new_steps or len(new_steps) == 0:
            raise ValueError("重规划结果为空")
        
        # 更新状态
        if keep_previous:
            # 保留之前的结果，只调整后续步骤
            completed_steps = state.get("step_results", [])[:starting_from-1]
            state["step_results"] = completed_steps
            state["current_step_index"] = starting_from - 1
        else:
            # 清空之前结果，重新开始
            state["step_results"] = []
            state["current_step_index"] = 0
        
        state["plan"] = new_steps
        state["current_step"] = new_steps[state["current_step_index"]] if new_steps else None
        state["should_replan"] = False
        state["replan_reason"] = None
        
        print(f"[Replaner] 重规划完成，新计划共 {len(new_steps)} 步，耗时 {elapsed:.2f}s")
        print(f"[Replaner] 调整原因: {adjustment_reason[:100]}...")
        print(f"[Replaner] 从第 {starting_from} 步开始执行")
        for i, step in enumerate(new_steps, 1):
            marker = "→" if i == starting_from else " "
            print(f"  {marker} {i}. {step}")
        
    except json.JSONDecodeError as e:
        print(f"[Replaner] JSON解析错误: {e}")
        _handle_replan_error(state, f"解析失败: {e}")
        
    except Exception as e:
        print(f"[Replaner] 重规划失败: {e}")
        _handle_replan_error(state, str(e))
    
    return update_state_timestamp(state)


def _build_replan_context(state: PlanExecuteState) -> str:
    """
    构建重规划的上下文信息
    
    Args:
        state: 当前状态
        
    Returns:
        str: 格式化的上下文字符串
    """
    lines = []
    
    # 原始输入
    lines.append(f"原始任务: {state['input']}")
    lines.append("")
    
    # 原始计划
    lines.append("原始计划:")
    for i, step in enumerate(state.get("original_plan", []), 1):
        lines.append(f"  {i}. {step}")
    lines.append("")
    
    # 当前计划
    lines.append("当前计划:")
    for i, step in enumerate(state.get("plan", []), 1):
        lines.append(f"  {i}. {step}")
    lines.append("")
    
    # 已执行步骤的结果
    step_results = state.get("step_results", [])
    if step_results:
        lines.append("已执行步骤结果:")
        for i, result in enumerate(step_results, 1):
            step_desc = result.get("step", f"步骤{i}")
            step_result = result.get("result", "")
            success = "成功" if result.get("success", True) else "失败"
            tool = result.get("tool_used", "")
            lines.append(f"  步骤{i}: {step_desc}")
            lines.append(f"    状态: {success}, 工具: {tool}")
            lines.append(f"    结果: {step_result[:150]}...")
        lines.append("")
    
    # 重规划原因
    replan_reason = state.get("replan_reason", "执行过程中需要调整")
    lines.append(f"重规划原因: {replan_reason}")
    lines.append("")
    
    # 当前进度
    current_index = state.get("current_step_index", 0)
    total_steps = len(state.get("plan", []))
    lines.append(f"当前进度: 第 {current_index}/{total_steps} 步")
    lines.append(f"重规划次数: {state.get('replan_count', 0)}/3")
    lines.append("")
    
    lines.append("请基于以上信息，制定新的执行计划。")
    
    return "\n".join(lines)


def _handle_replan_error(state: PlanExecuteState, error_msg: str):
    """
    处理重规划错误
    
    当重规划失败时，采用简化策略：
    1. 如果还有未执行的步骤，继续执行剩余步骤
    2. 如果所有步骤都执行过，标记为完成
    
    Args:
        state: 当前状态
        error_msg: 错误信息
    """
    print(f"[Replaner] 采用 fallback 策略")
    
    current_index = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    
    # 检查是否还有剩余步骤
    if current_index < len(plan):
        # 继续执行剩余步骤
        state["should_replan"] = False
        state["current_step"] = plan[current_index]
        print(f"[Replaner] 继续执行剩余步骤，从第 {current_index + 1} 步开始")
    else:
        # 所有步骤已执行，标记完成
        state["should_replan"] = False
        state["is_complete"] = True
        print(f"[Replaner] 所有步骤已执行，标记完成")
    
    state["error_message"] = f"重规划失败: {error_msg}"


def check_need_replan(state: PlanExecuteState) -> bool:
    """
    检查是否需要重规划
    
    基于执行结果和状态自动判断是否需要调整计划
    
    Args:
        state: 当前状态
        
    Returns:
        bool: 是否需要重规划
    """
    # 如果已经标记需要重规划，直接返回
    if state.get("should_replan", False):
        return True
    
    # 检查重规划次数
    if state.get("replan_count", 0) >= 3:
        return False
    
    step_results = state.get("step_results", [])
    
    # 如果最后一步失败，需要重规划
    if step_results and not step_results[-1].get("success", True):
        state["should_replan"] = True
        state["replan_reason"] = f"步骤执行失败: {step_results[-1].get('result', '')}"
        return True
    
    # 检查结果中是否包含需要调整的关键词
    if step_results:
        last_result = step_results[-1].get("result", "").lower()
        adjustment_keywords = [
            "需要更多信息", "信息不足", "无法确定", "需要确认",
            "缺少", "错误", "失败", "无法完成"
        ]
        if any(kw in last_result for kw in adjustment_keywords):
            state["should_replan"] = True
            state["replan_reason"] = "执行结果提示需要调整计划"
            return True
    
    return False
