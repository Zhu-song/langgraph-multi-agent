"""
Plan and Execute 工作流图

构建完整的 Plan-Execute 工作流，包含：
- Planner: 生成执行计划
- Executor: 执行单步任务
- Replanner: 动态调整计划
- Router: 路由判断
"""

from langgraph.graph import StateGraph, END, START

# 兼容不同版本的 langgraph 导入（与 workflow.py 保持一致）
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph.checkpoint.memory import MemorySaver as SqliteSaver
    except ImportError:
        SqliteSaver = None

import sqlite3
import os

from plan_execute.state import PlanExecuteState
from plan_execute.planner import planner_node
from plan_execute.executor import (
    executor_node, 
    should_continue, 
    generate_final_response
)
from plan_execute.replanner import replanner_node
from config import PLAN_EXECUTE_DB_PATH, MAX_PLAN_STEPS, ENABLE_REPLAN


def create_plan_execute_graph(checkpointer=None):
    """
    创建 Plan and Execute 工作流图
    
    Args:
        checkpointer: 可选的 checkpointer 实例
        
    Returns:
        StateGraph: 编译后的工作流图
    """
    
    # 创建工作流
    workflow = StateGraph(PlanExecuteState)
    
    # 添加节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)
    workflow.add_node("finalizer", generate_final_response)
    
    # 设置入口
    workflow.set_entry_point("planner")
    
    # 添加边
    # Planner -> Executor
    workflow.add_edge("planner", "executor")
    
    # Executor -> Router
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "continue": "executor",      # 继续执行下一步
            "replan": "replanner",       # 需要重规划
            "end": "finalizer"           # 结束，生成最终回答
        }
    )
    
    # Replanner -> Executor
    workflow.add_edge("replanner", "executor")
    
    # Finalizer -> END
    workflow.add_edge("finalizer", END)
    
    # 编译工作流
    if checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
    else:
        graph = workflow.compile()
    
    return graph


def create_plan_execute_graph_with_persistence(db_path: str = None):
    """
    创建带持久化的 Plan and Execute 工作流图
    
    Args:
        db_path: SQLite 数据库路径（默认使用 config.py 中的配置）
        
    Returns:
        StateGraph: 编译后的工作流图
    """
    if db_path is None:
        db_path = PLAN_EXECUTE_DB_PATH
    
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    
    # 创建 checkpointer
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    
    return create_plan_execute_graph(checkpointer=checkpointer)


# 创建默认工作流实例（带持久化）
try:
    plan_execute_graph = create_plan_execute_graph_with_persistence()
    print("[Plan-Execute] 工作流图创建成功（带持久化）")
except Exception as e:
    print(f"[Plan-Execute] 创建持久化工作流失败: {e}，使用内存模式")
    plan_execute_graph = create_plan_execute_graph()


def run_plan_execute(
    user_input: str, 
    thread_id: str = None,
    stream: bool = False
):
    """
    运行 Plan and Execute 工作流
    
    Args:
        user_input: 用户输入的任务描述
        thread_id: 可选的线程ID（用于持久化）
        stream: 是否使用流式输出
        
    Returns:
        如果 stream=False，返回最终状态
        如果 stream=True，返回生成器
    """
    from plan_execute.state import create_initial_state
    
    # 创建初始状态
    state = create_initial_state(user_input)
    
    # 配置
    config = {"configurable": {"thread_id": thread_id or "default"}}
    
    if stream:
        # 流式执行
        return _stream_plan_execute(state, config)
    else:
        # 同步执行
        return _sync_plan_execute(state, config)


def _sync_plan_execute(state: PlanExecuteState, config: dict):
    """同步执行工作流"""
    result = plan_execute_graph.invoke(state, config)
    return result


def _stream_plan_execute(state: PlanExecuteState, config: dict):
    """
    流式执行工作流
    
    产出执行过程中的各种事件
    """
    for event in plan_execute_graph.stream(state, config):
        # 解析事件类型
        if "planner" in event:
            yield {
                "type": "plan_generated",
                "data": {
                    "plan": event["planner"].get("plan", []),
                    "total_steps": len(event["planner"].get("plan", []))
                }
            }
        
        elif "executor" in event:
            step_results = event["executor"].get("step_results", [])
            if step_results:
                latest_result = step_results[-1]
                yield {
                    "type": "step_completed",
                    "data": {
                        "step_index": len(step_results),
                        "step": latest_result.get("step"),
                        "result": latest_result.get("result"),
                        "tool_used": latest_result.get("tool_used"),
                        "success": latest_result.get("success", True)
                    }
                }
        
        elif "replanner" in event:
            yield {
                "type": "plan_adjusted",
                "data": {
                    "new_plan": event["replanner"].get("plan", []),
                    "replan_count": event["replanner"].get("replan_count", 0)
                }
            }
        
        elif "finalizer" in event:
            yield {
                "type": "final_response",
                "data": {
                    "response": event["finalizer"].get("final_response", ""),
                    "total_steps": len(event["finalizer"].get("step_results", [])),
                    "completed": True
                }
            }


# 便捷的流式输出生成器
def stream_plan_execute_response(user_input: str, thread_id: str = None):
    """
    流式输出 Plan and Execute 执行结果
    
    适合用于 SSE 流式响应
    
    Args:
        user_input: 用户输入
        thread_id: 线程ID
        
    Yields:
        str: SSE 格式的数据行
    """
    import json
    
    yield f"data: {json.dumps({'type': 'start', 'data': {'input': user_input}}, ensure_ascii=False)}\n\n"
    
    try:
        for event in run_plan_execute(user_input, thread_id, stream=True):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}}, ensure_ascii=False)}\n\n"
    
    yield f"data: {json.dumps({'type': 'done', 'data': {}}, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    # 测试
    test_input = "查询北京今天的天气，然后给我写一份出行建议"
    print(f"\n测试输入: {test_input}\n")
    
    result = run_plan_execute(test_input)
    print("\n最终结果:")
    print(result.get("final_response", "无结果"))
    print(f"\n执行步骤数: {len(result.get('step_results', []))}")
    print(f"重规划次数: {result.get('replan_count', 0)}")
