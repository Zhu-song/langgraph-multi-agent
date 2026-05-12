"""
Plan and Execute 工具

对外暴露的工具接口，允许主 Agent 调用 Plan-Execute 功能
"""

import json
import asyncio
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from plan_execute.graph import run_plan_execute


class PlanExecuteInput(BaseModel):
    """Plan-Execute 工具输入参数"""
    task: str = Field(
        description="需要执行的任务描述，支持复杂多步骤任务",
        examples=["查询北京天气并写出行建议", "计算 1+1 的结果"]
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="可选的线程ID，用于持久化执行状态"
    )


def plan_execute_func(task: str, thread_id: Optional[str] = None) -> str:
    """
    Plan and Execute 工具
    
    将复杂任务分解为多个步骤执行，适用于：
    - 需要多步骤完成的任务
    - 涉及多个工具调用的任务
    - 需要规划和执行分离的任务
    
    Args:
        task: 任务描述
        thread_id: 可选的线程ID
        
    Returns:
        str: 执行结果，包含计划和最终结果
    """
    try:
        print(f"[Plan-Execute Tool] 开始执行任务: {task[:50]}...")
        
        # 执行 Plan-Execute 工作流
        result = run_plan_execute(
            user_input=task,
            thread_id=thread_id or "tool_call",
            stream=False
        )
        
        # 构建输出
        plan = result.get("plan", [])
        step_results = result.get("step_results", [])
        final_response = result.get("final_response", "")
        replan_count = result.get("replan_count", 0)
        
        output_lines = []
        output_lines.append("=" * 50)
        output_lines.append("📋 任务执行计划")
        output_lines.append("=" * 50)
        
        # 显示计划
        for i, step in enumerate(plan, 1):
            output_lines.append(f"  {i}. {step}")
        
        output_lines.append("")
        output_lines.append("=" * 50)
        output_lines.append("✅ 执行结果")
        output_lines.append("=" * 50)
        
        # 显示执行结果
        for i, sr in enumerate(step_results, 1):
            step_desc = sr.get("step", f"步骤{i}")
            tool_used = sr.get("tool_used", "")
            success = "✓" if sr.get("success", True) else "✗"
            step_result = sr.get("result", "")[:150]
            output_lines.append(f"  {success} 步骤{i}: {step_desc}")
            output_lines.append(f"     工具: {tool_used}")
            output_lines.append(f"     结果: {step_result}...")
            output_lines.append("")
        
        if replan_count > 0:
            output_lines.append(f"🔄 重规划次数: {replan_count}")
            output_lines.append("")
        
        output_lines.append("=" * 50)
        output_lines.append("📝 最终回答")
        output_lines.append("=" * 50)
        output_lines.append(final_response)
        
        return "\n".join(output_lines)
        
    except Exception as e:
        print(f"[Plan-Execute Tool] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return f"Plan-Execute 执行失败: {str(e)}"


# 创建工具实例
plan_execute_tool = StructuredTool.from_function(
    name="plan_execute",
    func=plan_execute_func,
    description="""用于执行复杂多步骤任务的工具。

适用场景：
1. 需要多个步骤才能完成的任务
2. 涉及多个工具调用的任务
3. 需要先规划后执行的任务
4. 任务描述中包含"先...然后..."、"查询...并..."等关键词

使用示例：
- "查询北京天气，然后写一份出行建议"
- "先搜索最新新闻，再总结要点"
- "计算公司利润并生成报表"

注意事项：
- 该工具会自动将任务分解为多个步骤
- 每个步骤会调用合适的工具执行
- 执行失败时会自动重规划（最多3次）
- 返回完整的执行计划和最终结果
""",
    args_schema=PlanExecuteInput
)


# 异步版本（供内部使用）
async def plan_execute_async(task: str, thread_id: Optional[str] = None) -> str:
    """
    Plan-Execute 异步版本
    
    Args:
        task: 任务描述
        thread_id: 可选的线程ID
        
    Returns:
        str: 执行结果
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, plan_execute_func, task, thread_id)


if __name__ == "__main__":
    # 测试工具
    print("🧪 测试 Plan-Execute 工具\n")
    
    test_task = "计算 100 + 200 的结果"
    print(f"测试任务: {test_task}\n")
    
    result = plan_execute_tool.invoke({"task": test_task})
    print(result)
