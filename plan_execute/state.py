"""
Plan and Execute 状态定义

定义 Plan-Execute 工作流中使用的状态类型
"""

from typing import TypedDict, List, Optional, Any
from datetime import datetime


class StepResult(TypedDict):
    """单步执行结果"""
    step: str                           # 步骤描述
    result: str                         # 执行结果
    tool_used: Optional[str]            # 使用的工具名称
    success: bool                       # 是否成功
    duration: float                     # 执行耗时（秒）
    timestamp: str                      # 执行时间戳


class PlanExecuteState(TypedDict):
    """
    Plan and Execute 工作流状态
    
    包含任务规划、执行、重规划的全生命周期状态
    """
    # 输入
    input: str                          # 用户原始输入
    
    # 计划相关
    plan: List[str]                     # 计划步骤列表，如 ["查询北京天气", "写出行建议"]
    original_plan: List[str]            # 原始计划（用于对比重规划）
    
    # 执行相关
    current_step_index: int             # 当前执行到第几步（从0开始）
    current_step: Optional[str]         # 当前步骤描述
    step_results: List[StepResult]      # 已执行步骤的结果列表
    
    # 重规划相关
    should_replan: bool                 # 是否需要重新规划
    replan_reason: Optional[str]        # 重规划原因
    replan_count: int                   # 重规划次数（防止无限循环）
    
    # 输出
    final_response: Optional[str]       # 最终回答
    is_complete: bool                   # 是否完成
    
    # 元数据
    created_at: str                     # 创建时间
    updated_at: str                     # 更新时间
    error_message: Optional[str]        # 错误信息


def create_initial_state(user_input: str) -> PlanExecuteState:
    """
    创建初始状态
    
    Args:
        user_input: 用户输入的任务描述
        
    Returns:
        PlanExecuteState: 初始化的状态对象
    """
    now = datetime.now().isoformat()
    return {
        "input": user_input,
        "plan": [],
        "original_plan": [],
        "current_step_index": 0,
        "current_step": None,
        "step_results": [],
        "should_replan": False,
        "replan_reason": None,
        "replan_count": 0,
        "final_response": None,
        "is_complete": False,
        "created_at": now,
        "updated_at": now,
        "error_message": None
    }


def update_state_timestamp(state: PlanExecuteState) -> PlanExecuteState:
    """更新状态的时间戳"""
    state["updated_at"] = datetime.now().isoformat()
    return state
