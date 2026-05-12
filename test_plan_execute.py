"""
Plan-Execute 工作流测试脚本

测试验证 Plan-Execute 模块是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试 1: 模块导入")
    print("=" * 60)
    
    try:
        from plan_execute import plan_execute_graph, PlanExecuteState, StepResult
        print("✅ plan_execute 模块导入成功")
        
        from plan_execute.state import create_initial_state
        print("✅ state 模块导入成功")
        
        from plan_execute.planner import planner_node
        print("✅ planner 模块导入成功")
        
        from plan_execute.executor import executor_node, should_continue
        print("✅ executor 模块导入成功")
        
        from plan_execute.replanner import replanner_node
        print("✅ replanner 模块导入成功")
        
        from plan_execute.graph import run_plan_execute
        print("✅ graph 模块导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_creation():
    """测试状态创建"""
    print("\n" + "=" * 60)
    print("测试 2: 状态创建")
    print("=" * 60)
    
    try:
        from plan_execute.state import create_initial_state
        
        state = create_initial_state("测试任务")
        
        print(f"✅ 初始状态创建成功")
        print(f"   - input: {state['input']}")
        print(f"   - plan: {state['plan']}")
        print(f"   - current_step_index: {state['current_step_index']}")
        print(f"   - is_complete: {state['is_complete']}")
        
        return True
    except Exception as e:
        print(f"❌ 状态创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_creation():
    """测试工作流图创建"""
    print("\n" + "=" * 60)
    print("测试 3: 工作流图创建")
    print("=" * 60)
    
    try:
        from plan_execute.graph import create_plan_execute_graph
        
        # 创建不带持久化的工作流图
        graph = create_plan_execute_graph()
        
        print("✅ 工作流图创建成功")
        print(f"   - 节点数: {len(graph.nodes)}")
        print(f"   - 节点列表: {list(graph.nodes.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ 工作流图创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_planner_node():
    """测试规划器节点"""
    print("\n" + "=" * 60)
    print("测试 4: 规划器节点")
    print("=" * 60)
    
    try:
        from plan_execute.state import create_initial_state
        from plan_execute.planner import planner_node
        
        state = create_initial_state("计算 123 + 456 的结果")
        
        print("调用规划器...")
        result = planner_node(state)
        
        print(f"✅ 规划器执行成功")
        print(f"   - 生成的计划: {result.get('plan', [])}")
        print(f"   - 当前步骤: {result.get('current_step')}")
        
        return True
    except Exception as e:
        print(f"❌ 规划器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_executor_node():
    """测试执行器节点"""
    print("\n" + "=" * 60)
    print("测试 5: 执行器节点")
    print("=" * 60)
    
    try:
        from plan_execute.state import create_initial_state
        
        # 创建一个简单的测试状态
        state = create_initial_state("测试")
        state["plan"] = ["计算 1+1"]
        state["current_step"] = "计算 1+1"
        state["current_step_index"] = 0
        
        from plan_execute.executor import executor_node
        
        print("调用执行器...")
        result = executor_node(state)
        
        print(f"✅ 执行器执行成功")
        if result.get("step_results"):
            step_result = result["step_results"][0]
            print(f"   - 步骤: {step_result.get('step')}")
            print(f"   - 工具: {step_result.get('tool_used')}")
            print(f"   - 成功: {step_result.get('success')}")
            print(f"   - 结果: {step_result.get('result', '')[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ 执行器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "=" * 60)
    print("测试 6: 完整工作流")
    print("=" * 60)
    
    try:
        from plan_execute.graph import create_plan_execute_graph
        from plan_execute.state import create_initial_state
        
        # 创建工作流图（不带持久化，避免数据库问题）
        graph = create_plan_execute_graph()
        
        # 创建初始状态
        test_input = "计算 10 + 20 的结果"
        state = create_initial_state(test_input)
        
        print(f"测试输入: {test_input}")
        print("执行工作流...")
        
        # 执行工作流
        result = graph.invoke(state)
        
        print(f"\n✅ 工作流执行成功")
        print(f"   - 执行步骤数: {len(result.get('step_results', []))}")
        print(f"   - 重规划次数: {result.get('replan_count', 0)}")
        print(f"   - 是否完成: {result.get('is_complete', False)}")
        
        if result.get("final_response"):
            print(f"\n📝 最终回答:")
            print(f"   {result['final_response'][:200]}...")
        
        return True
    except Exception as e:
        print(f"❌ 完整工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("Plan-Execute 工作流测试")
    print("🚀" * 30 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("模块导入", test_imports()))
    results.append(("状态创建", test_state_creation()))
    results.append(("工作流图创建", test_graph_creation()))
    
    # 以下测试需要 LLM API，仅在配置正确时运行
    try:
        from config import llm
        print("\n检测到 LLM 配置，运行 LLM 相关测试...")
        results.append(("规划器节点", test_planner_node()))
        results.append(("执行器节点", test_executor_node()))
        results.append(("完整工作流", test_full_workflow()))
    except Exception as e:
        print(f"\n⚠️ 跳过 LLM 相关测试: {e}")
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Plan-Execute 工作流工作正常。")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
