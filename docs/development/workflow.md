# LangGraph 工作流详解

本文档详细介绍 LangGraph 工作流的设计与实现。

## 工作流概述

本项目采用 **ReAct（Reasoning + Acting）** 架构，通过 LangGraph 的 `StateGraph` 构建多智能体工作流。

### 核心思想

```
LLM 不是一次性生成回答，而是：
1. 思考（Reasoning）：分析问题，决定是否需要工具
2. 行动（Acting）：调用工具获取信息
3. 循环：基于工具结果继续思考，直到生成最终答案
```

---

## 状态图结构

### 完整状态图

```
                    ┌──────────────────────────────────┐
                    │           START                   │
                    └──────────────┬───────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │         llm_agent 节点            │
                    │  • 加载系统提示词 + 对话历史       │
                    │  • LLM 推理（是否调用工具）        │
                    │  • 长对话自动压缩（>6轮）          │
                    └──────────────┬───────────────────┘
                                   │
                          ┌────────┴────────┐
                          │   my_router     │
                          │  有 tool_calls?  │
                          └────────┬────────┘
                          ┌────────┴────────┐
                         Yes                No
                          │                 │
                          ▼                 ▼
              ┌─────────────────┐      ┌─────────┐
              │  tool_subgraph  │      │   END   │
              │                 │      └─────────┘
              │  ┌───────────┐  │
              │  │human_check│  │──── 高危工具 → interrupt()
              │  └─────┬─────┘  │         等待人工审核
              │        ▼        │
              │  ┌───────────┐  │
              │  │ Tool Node  │  │──── 执行工具，返回结果
              │  └───────────┘  │
              └────────┬────────┘
                       │
                       ▼
              回到 llm_agent（继续推理）
```

---

## 核心节点详解

### 1. llm_agent 节点

**职责**：LLM 推理与决策

```python
def llm_agent(state: AgentState):
    """LLM 推理节点"""
    # 1. 加载系统提示词
    system_prompt = SUPERVISOR_PROMPT
    
    # 2. 加载对话历史
    messages = state["messages"]
    
    # 3. 长对话压缩（超过6轮）
    if len(messages) > 12:  # 6轮 = 12条消息
        messages = compress_history(messages)
    
    # 4. 调用 LLM
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}
```

**关键逻辑**：
- **工具绑定**：`llm.bind_tools(tools)` 将 16 个工具绑定到 LLM
- **历史压缩**：超过 6 轮自动总结，保留最近 2 轮
- **系统提示词**：定义工具能力边界和调用规则

### 2. my_router 节点

**职责**：判断是否需要调用工具

```python
def my_router(state: AgentState):
    """路由判断节点"""
    last_message = state["messages"][-1]
    
    # 检查是否有 tool_calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # 有工具调用 → 派发到 tool_subgraph
        return [Send("tool_subgraph", {
            "messages": [last_message]
        })]
    else:
        # 无工具调用 → 结束
        return END
```

**关键逻辑**：
- **工具检测**：检查 LLM 响应是否包含 `tool_calls`
- **Send 派发**：使用 LangGraph `Send` API 并行派发多个工具调用
- **条件终止**：无工具调用时结束工作流

### 3. tool_subgraph 子图

**职责**：工具执行（含人工审核）

```python
# 工具执行子图
tool_subgraph = StateGraph(ToolState)
tool_subgraph.add_node("human_approval", human_approval)
tool_subgraph.add_node("tool_node", ToolNode(tools))
tool_subgraph.add_edge("human_approval", "tool_node")
tool_subgraph.set_entry_point("human_approval")
```

**子图流程**：
```
进入子图 → human_approval 检查 → tool_node 执行 → 返回结果
```

### 4. human_approval 节点

**职责**：高危工具人工审核

```python
def human_approval(state: ToolState):
    """人工审核节点"""
    HIGH_RISK_TOOLS = {
        "web_search",
        "file_delete",
        "database_write",
        "file_write",
    }
    
    last_message = state["messages"][-1]
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in HIGH_RISK_TOOLS:
            # 触发 interrupt，暂停工作流
            interrupt({
                "tool_name": tool_call["name"],
                "args": tool_call["args"]
            })
    
    return state
```

**关键逻辑**：
- **高危检测**：检查工具是否在 `HIGH_RISK_TOOLS` 集合中
- **interrupt()**：触发 LangGraph 中断机制，工作流暂停
- **状态保存**：中断时状态自动保存到 SQLite

---

## 状态管理

### AgentState 定义

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """Agent 状态定义"""
    messages: Annotated[list, add_messages]
    # messages 是核心状态，包含：
    # - HumanMessage: 用户消息
    # - AIMessage: AI 回答（可能包含 tool_calls）
    # - ToolMessage: 工具执行结果
```

### 状态持久化

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 创建持久化存储
memory = SqliteSaver.from_conn_string("agent_memory.db")

# 编译工作流时绑定
graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_approval"]  # 在审核前中断
)
```

### 状态恢复

```python
# 检查是否有待处理的 interrupt
state = graph.get_state(config)
if state.tasks:
    # 有待处理的 interrupt
    pending_tool = state.tasks[0]
    
    # 恢复执行（通过审核）
    graph.invoke(
        Command(resume="yes"),
        config
    )
```

---

## 工具调用流程

### 完整流程

```
1. LLM 决策
   └── llm.bind_tools(tools) 绑定 16 个工具
   └── LLM 根据问题自主决定调用哪些工具

2. 路由派发
   └── my_router 检测 tool_calls
   └── Send API 并行派发到 tool_subgraph

3. 人工审核
   └── human_approval 检查是否高危工具
   └── 高危 → interrupt() 暂停
   └── 安全 → 直接执行

4. 工具执行
   └── ToolNode 执行具体工具函数
   └── 返回 ToolMessage

5. 结果回传
   └── ToolMessage 回到 llm_agent
   └── LLM 基于结果继续推理
   └── 循环直到生成最终答案
```

### 并行工具调用

LangGraph 支持并行调用多个工具：

```python
# LLM 同时决定调用多个工具
response = llm.invoke("计算 1+2 和 3+4")

# response.tool_calls 包含:
# [
#   {"name": "calculator", "args": {"expression": "1+2"}},
#   {"name": "calculator", "args": {"expression": "3+4"}}
# ]

# my_router 使用 Send 并行派发
return [
    Send("tool_subgraph", {"messages": [call1]}),
    Send("tool_subgraph", {"messages": [call2]}),
]
```

---

## 长对话管理

### 自动压缩机制

```python
def compress_history(messages: list) -> list:
    """长对话自动压缩"""
    if len(messages) <= 12:
        return messages
    
    # 保留系统提示词
    system_msg = messages[0]
    
    # 保留最近 2 轮（4条消息）
    recent = messages[-4:]
    
    # 中间部分用 LLM 总结
    middle = messages[1:-4]
    summary = llm.invoke(f"总结以下对话:\n{middle}")
    
    return [
        system_msg,
        HumanMessage(content=f"[历史对话总结]\n{summary.content}"),
        *recent
    ]
```

### 压缩策略

| 条件 | 动作 |
|------|------|
| ≤ 6 轮 | 不压缩 |
| > 6 轮 | 总结历史，保留最近 2 轮 |

---

## SSE 流式输出

### 流式实现

```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE 流式对话"""
    config = {
        "configurable": {"thread_id": request.user_id}
    }
    
    async def event_generator():
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=request.message)]},
            config,
            version="v2"
        ):
            if event["event"] == "on_chat_model_stream":
                # 提取流式 Token
                token = event["data"]["chunk"].content
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
            
            elif event["event"] == "on_tool_start":
                # 工具调用开始
                yield f"data: {json.dumps({'tool_start': event['name']})}\n\n"
            
            elif event["event"] == "on_tool_end":
                # 工具调用结束
                yield f"data: {json.dumps({'tool_end': event['name']})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### 前端处理

```javascript
// 前端 SSE 处理
const eventSource = new EventSource('/chat/stream')

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.token) {
        appendMessage(data.token)  // 追加 Token
    } else if (data.tool_start) {
        showToolStatus(data.tool_start, 'running')
    } else if (data.tool_end) {
        showToolStatus(data.tool_end, 'done')
    }
}
```

---

## 五层保护链

### 装饰器架构

```
请求 → global_fallback → retry → degrade → trace_log → rate_limit → 核心函数
```

### 各层详解

| 层级 | 装饰器 | 作用 |
|------|--------|------|
| 1 | `global_fallback` | 全局兜底，任何异常返回通用回答 |
| 2 | `retry` | 失败自动重试（默认 2 次） |
| 3 | `degrade_strategy` | 三级降级策略 |
| 4 | `agent_trace_log` | 链路日志，按天切割 |
| 5 | `rate_limit` | 会话级限流 + 幂等防重复 |

### 降级策略

```python
def degrade_strategy(func):
    """三级降级策略"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SearchError:
            # 搜索失败 → 使用本地知识库
            return local_knowledge_query(args[0])
        except RAGError:
            # RAG 失败 → 使用通用常识
            return general_knowledge(args[0])
        except Exception:
            # 其他异常 → 极简问答
            return "抱歉，服务暂时不可用，请稍后重试。"
    return wrapper
```

---

## Plan-Execute 工作流

### 概述

除了 ReAct 推理循环，项目还支持 **Plan-Execute** 模式，适用于复杂的多步骤任务。

### 工作原理

```
用户输入复杂任务
    ↓
Planner：LLM 将任务分解为有序步骤
    ↓
Executor：逐步执行每个步骤（调用工具）
    ↓
Replanner：检查执行结果，必要时调整计划
    ↓
循环直到所有步骤完成
    ↓
汇总所有步骤结果，生成最终回答
```

### 状态图

```
┌───────────┐    ┌───────────┐    ┌───────────┐
│  Planner  │───▶│  Executor │───▶│ Replanner │
│ (制定计划) │    │ (执行步骤) │    │ (动态调整) │
└───────────┘    └───────────┘    └─────┬─────┘
                      ▲                  │
                      │    ┌─────────┐   │
                      └────│  END    │◀──┘
                           │(全部完成)│
                           └─────────┘
```

### 与 ReAct 模式的区别

| 特性 | ReAct | Plan-Execute |
|------|-------|-------------|
| 推理方式 | 单步推理循环 | 先规划后执行 |
| 适用场景 | 简单到中等任务 | 复杂多步骤任务 |
| 工具调用 | 按需调用 | 按计划调用 |
| 动态调整 | 每轮重新决策 | Replanner 调整 |
| 可观测性 | 推理过程透明 | 计划步骤透明 |

### 使用方式

通过前端选择 "Plan-Execute" 对话模式，或调用 API：

```python
# API 调用
resp = requests.post(f"{BASE_URL}/plan-execute/stream", json={
    "user_id": user_id,
    "message": "帮我调研并总结AI行业发展趋势"
})
```

---

## 配置与定制

### 修改高危工具列表

编辑 `config.py`：

```python
HIGH_RISK_TOOLS = {
    "web_search",
    "file_delete",
    "database_write",
    "file_write",
    # 添加自定义高危工具
}
```

### 修改压缩策略

编辑 `workflow.py`：

```python
# 修改压缩阈值
COMPRESS_THRESHOLD = 12  # 默认 12 条消息（6轮）

# 修改保留轮数
KEEP_RECENT_TURNS = 2    # 默认保留最近 2 轮
```

### 修改重试策略

编辑 `utils/retry.py`：

```python
# 修改默认重试次数
DEFAULT_MAX_RETRIES = 3  # 默认 2 次

# 修改重试间隔
RETRY_DELAYS = [1, 2, 4]  # 指数退避
```

---

## 调试技巧

### 查看工作流执行

```python
# 打印工作流图
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

### 查看状态历史

```python
# 获取所有状态快照
for state in graph.get_state_history(config):
    print(state.values)
    print(state.next)
    print("---")
```

### 查看工具调用

```python
# 在 llm_agent 中添加日志
def llm_agent(state: AgentState):
    last_msg = state["messages"][-1]
    
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        for call in last_msg.tool_calls:
            logger.info(f"工具调用: {call['name']}, 参数: {call['args']}")
    
    # ... 正常逻辑
```

---

## 下一步

- [工具开发指南](./tools.md) - 学习如何添加自定义工具
- [API 接口文档](./api.md) - 查看 REST API 详情
- [架构设计](./architecture.md) - 了解整体系统架构
