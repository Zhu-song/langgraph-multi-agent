"""
规划器节点 (Planner)

将用户输入的复杂任务拆解为可执行的子任务步骤列表
"""

import json
import time
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from config import llm
from plan_execute.state import PlanExecuteState, update_state_timestamp


PLANNER_SYSTEM_PROMPT = """你是一个任务规划专家。你的职责是将用户的复杂任务拆解为清晰、可执行的步骤。

规划原则：
1. 每个步骤应该是原子性的，只完成一个具体任务
2. 步骤之间应该有逻辑顺序，避免循环依赖
3. 步骤描述要清晰明确，包含必要的上下文信息
4. 步骤数量控制在 2-8 步之间，避免过于细碎或笼统
5. 优先使用系统工具来完成任务（搜索、计算、翻译等）

可用工具说明：
- web_search: 联网搜索最新信息
- calculator: 数学计算
- translate: 中英翻译
- summary: 文本摘要
- rag_knowledge_query: 查询知识库
- time_tool: 获取时间信息

输出格式要求：
必须返回 JSON 格式，包含以下字段：
{
    "steps": ["步骤1", "步骤2", "步骤3"],
    "reasoning": "规划思路说明"
}

注意：
- 只输出 JSON，不要输出其他内容
- 步骤描述使用中文
- 确保步骤可独立执行"""


def planner_node(state: PlanExecuteState) -> PlanExecuteState:
    """
    规划器节点：生成任务执行计划
    
    Args:
        state: 当前状态，包含用户输入
        
    Returns:
        PlanExecuteState: 更新后的状态，包含生成的计划
    """
    print(f"[Planner] 开始规划任务: {state['input'][:50]}...")
    
    try:
        # 构建消息
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"请为以下任务制定执行计划：\n\n{state['input']}")
        ]
        
        # 调用 LLM 生成计划
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
        plan_data = json.loads(content)
        steps = plan_data.get("steps", [])
        reasoning = plan_data.get("reasoning", "")
        
        # 验证步骤
        if not steps or len(steps) == 0:
            raise ValueError("规划结果为空")
        
        if len(steps) > 10:
            steps = steps[:10]  # 限制最大步骤数
            print(f"[Planner] 警告：步骤过多，已截断至10步")
        
        # 更新状态
        state["plan"] = steps
        state["original_plan"] = steps.copy()
        state["current_step_index"] = 0
        state["current_step"] = steps[0] if steps else None
        state["should_replan"] = False
        state["replan_reason"] = None
        
        print(f"[Planner] 规划完成，共 {len(steps)} 步，耗时 {elapsed:.2f}s")
        print(f"[Planner] 规划思路: {reasoning[:100]}...")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
        
    except json.JSONDecodeError as e:
        print(f"[Planner] JSON解析错误: {e}")
        state["error_message"] = f"规划结果解析失败: {e}"
        # 使用简单 fallback 计划
        state["plan"] = [state["input"]]
        state["original_plan"] = [state["input"]]
        state["current_step"] = state["input"]
        
    except Exception as e:
        print(f"[Planner] 规划失败: {e}")
        state["error_message"] = f"规划失败: {e}"
        # 使用简单 fallback 计划
        state["plan"] = [state["input"]]
        state["original_plan"] = [state["input"]]
        state["current_step"] = state["input"]
    
    return update_state_timestamp(state)


def planner_node_stream(state: PlanExecuteState):
    """
    规划器节点（流式版本）
    
    生成计划的同时产出流式事件
    
    Yields:
        dict: 流式事件，包含类型和数据
    """
    print(f"[Planner] 开始规划任务: {state['input'][:50]}...")
    
    yield {
        "type": "plan_start",
        "data": {"input": state["input"]}
    }
    
    try:
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"请为以下任务制定执行计划：\n\n{state['input']}")
        ]
        
        # 流式调用
        full_content = ""
        for chunk in llm.stream(messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            full_content += content
        
        # 解析 JSON
        content = full_content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        plan_data = json.loads(content)
        steps = plan_data.get("steps", [])
        
        # 更新状态
        state["plan"] = steps
        state["original_plan"] = steps.copy()
        state["current_step_index"] = 0
        state["current_step"] = steps[0] if steps else None
        
        yield {
            "type": "plan_complete",
            "data": {
                "steps": steps,
                "total_steps": len(steps)
            }
        }
        
    except Exception as e:
        print(f"[Planner] 规划失败: {e}")
        state["error_message"] = f"规划失败: {e}"
        state["plan"] = [state["input"]]
        state["original_plan"] = [state["input"]]
        state["current_step"] = state["input"]
        
        yield {
            "type": "plan_error",
            "data": {"error": str(e)}
        }
    
    # 生成器函数中 return 值不会被调用方接收，
    # 改为在 yield 之前直接更新状态时间戳
    state = update_state_timestamp(state)
