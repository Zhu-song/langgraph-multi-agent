# API 接口文档

本文档详细介绍 LangGraph 多智能体助手的 REST API 接口。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs`（Swagger UI）
- **数据格式**: JSON
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应

```json
{
    "code": 200,
    "message": "success",
    "data": { ... }
}
```

### 错误响应

```json
{
    "code": 500,
    "message": "错误描述",
    "reply": "用户可见的错误提示"
}
```

### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 用户认证接口

### 注册

```http
POST /api/auth/register
```

**请求体**:
```json
{
    "username": "testuser",
    "password": "password123"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "注册成功",
    "data": {
        "user_id": "user_xxx",
        "username": "testuser"
    }
}
```

### 登录

```http
POST /api/auth/login
```

**请求体**:
```json
{
    "username": "testuser",
    "password": "password123"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "user_id": "user_xxx",
        "username": "testuser",
        "token": "jwt_token_xxx"
    }
}
```

### 修改密码

```http
POST /api/auth/change-password
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "old_password": "old_password",
    "new_password": "new_password"
}
```

### 删除用户

```http
POST /api/auth/delete-user
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "password": "password123"
}
```

---

## 对话接口

### 普通对话（同步）

```http
POST /chat
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "conversation_id": "conv_xxx",
    "message": "你好，请介绍一下你自己"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "success",
    "reply": "我是 LangGraph 多智能体助手...",
    "conversation_id": "conv_xxx"
}
```

### 流式对话（SSE）

```http
POST /chat/stream
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "conversation_id": "conv_xxx",
    "message": "写一首关于春天的诗"
}
```

**响应**: `text/event-stream`

```
data: {"token": "春"}
data: {"token": "天"}
data: {"token": "来"}
data: {"token": "了"}
...
data: [DONE]
```

### RAG 问答

```http
POST /rag
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "conversation_id": "conv_xxx",
    "message": "根据知识库，公司的年假政策是什么？"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "success",
    "reply": "根据《员工手册》，年假政策如下：...",
    "sources": [
        {
            "document": "员工手册.pdf",
            "score": 0.92,
            "snippet": "入职满1年享受5天年假..."
        }
    ]
}
```

### RAG 流式输出

```http
POST /rag/stream
```

**请求体**: 同 `/rag`

**响应**: `text/event-stream`（流式输出 RAG 结果）

### 真实 RAG 流式输出

```http
POST /rag/real/stream
```

**请求体**: 同 `/rag`

**响应**: `text/event-stream`（逐字流式输出）

---

## 对话管理接口

### 创建对话

```http
POST /api/conversations/create
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "title": "测试对话",
    "mode": "smart_chat"
}
```

**对话模式**:

| mode | 说明 |
|------|------|
| `smart_chat` | 智能对话 |
| `stream_chat` | 流式对话 |
| `rag_chat` | RAG 问答 |
| `rag_stream` | RAG 流式 |
| `rag_real_stream` | 真实 RAG 流式 |

**响应**:
```json
{
    "code": 200,
    "data": {
        "conversation_id": "conv_xxx",
        "title": "测试对话",
        "mode": "smart_chat",
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

### 获取对话列表

```http
GET /api/conversations/list?user_id=user_xxx
```

**响应**:
```json
{
    "code": 200,
    "data": [
        {
            "conversation_id": "conv_1",
            "title": "对话1",
            "mode": "smart_chat",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:00:00Z",
            "pinned": false
        }
    ]
}
```

### 删除对话

```http
POST /api/conversations/delete
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "conversation_id": "conv_xxx"
}
```

### 重命名对话

```http
POST /api/conversations/rename
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "conversation_id": "conv_xxx",
    "new_title": "新标题"
}
```

### 置顶对话

```http
POST /api/conversations/pin
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "conversation_id": "conv_xxx",
    "pinned": true
}
```

### 获取对话历史

```http
GET /api/conversations/messages?user_id=user_xxx&conversation_id=conv_xxx
```

**响应**:
```json
{
    "code": 200,
    "data": [
        {
            "role": "user",
            "content": "你好",
            "created_at": "2024-01-15T10:30:00Z"
        },
        {
            "role": "assistant",
            "content": "你好！我是 LangGraph 多智能体助手...",
            "created_at": "2024-01-15T10:30:01Z"
        }
    ]
}
```

---

## 知识库接口

### 更新知识库

```http
POST /knowledge/update
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "mode": "incremental"
}
```

**更新模式**:

| mode | 说明 |
|------|------|
| `incremental` | 增量更新（推荐） |
| `full` | 全量更新 |

**响应**:
```json
{
    "code": 200,
    "message": "知识库更新成功",
    "data": {
        "total_docs": 15,
        "indexed_docs": 15,
        "new_docs": 2,
        "updated_docs": 0
    }
}
```

### 获取知识库状态

```http
GET /api/knowledge/status?user_id=user_xxx
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "total_documents": 15,
        "indexed_documents": 15,
        "status": "ready",
        "last_updated": "2024-01-15T10:30:00Z",
        "chroma_db_size": "125MB"
    }
}
```

### 构建知识图谱

```http
POST /api/knowledge/graph/build
```

**请求体**:
```json
{
    "user_id": "user_xxx"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "知识图谱构建成功",
    "data": {
        "entities": 120,
        "relations": 350,
        "processing_time": "45s"
    }
}
```

### 上传文档

```http
POST /api/knowledge/upload
```

**请求**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户 ID |
| `files` | file[] | 文件列表（支持多选） |

**响应**:
```json
{
    "code": 200,
    "message": "上传成功",
    "data": {
        "uploaded_files": ["doc1.pdf", "doc2.md"],
        "total_size": "15MB"
    }
}
```

---

## 人工审核接口

### 检查审核状态

```http
GET /api/approval/check/{user_id}
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "has_pending": true,
        "pending_count": 2,
        "requests": [
            {
                "tool_call_id": "call_xxx",
                "tool_name": "web_search",
                "args": {"query": "AI新闻"},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]
    }
}
```

### 处理审核

```http
POST /api/approval/resume
```

**请求体**:
```json
{
    "user_id": "user_xxx",
    "decision": "yes",
    "tool_call_id": "call_xxx"
}
```

**参数说明**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户 ID |
| `decision` | string | `"yes"` 通过 / `"no"` 拒绝 |
| `tool_call_id` | string | 工具调用 ID |

**响应**:
```json
{
    "code": 200,
    "message": "审核处理成功",
    "data": {
        "decision": "yes",
        "tool_name": "web_search",
        "status": "executed"
    }
}
```

### 获取审核历史

```http
GET /api/approval/history?user_id=user_xxx&limit=20
```

**响应**:
```json
{
    "code": 200,
    "data": [
        {
            "tool_call_id": "call_xxx",
            "tool_name": "web_search",
            "args": {"query": "AI新闻"},
            "decision": "yes",
            "operator": "admin",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    ]
}
```

---

## SSE 事件格式

### 流式对话事件

| 事件类型 | 数据格式 | 说明 |
|----------|----------|------|
| `token` | `{"token": "字"}` | 流式 Token |
| `tool_start` | `{"tool_start": "calculator"}` | 工具开始执行 |
| `tool_end` | `{"tool_end": "calculator", "result": "..."}` | 工具执行完成 |
| `tool_call` | `{"tool_call": "web_search", "args": {...}}` | 高危工具等待审核 |
| `error` | `{"error": "错误信息"}` | 错误 |
| `[DONE]` | - | 流结束 |

### 前端处理示例

```javascript
const eventSource = new EventSource('/chat/stream')

eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
        eventSource.close()
        return
    }
    
    const data = JSON.parse(event.data)
    
    switch (true) {
        case data.token !== undefined:
            appendToken(data.token)
            break
        case data.tool_start !== undefined:
            showToolStatus(data.tool_start, 'running')
            break
        case data.tool_end !== undefined:
            showToolResult(data.tool_end, data.result)
            break
        case data.tool_call !== undefined:
            showApprovalRequest(data.tool_call, data.args)
            break
        case data.error !== undefined:
            showError(data.error)
            break
    }
}
```

---

## 错误处理

### 全局异常处理

所有未捕获异常都会被全局异常处理器捕获：

```json
{
    "code": 500,
    "message": "服务器内部错误: 具体错误信息",
    "reply": "❌ 服务异常: 用户可见的友好提示"
}
```

### 常见错误码

| 错误码 | 说明 | 解决方法 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求体格式 |
| 401 | 未认证 | 重新登录获取 Token |
| 403 | 无权限 | 检查用户权限 |
| 404 | 资源不存在 | 检查 URL 和参数 |
| 422 | 参数验证失败 | 检查必填字段 |
| 429 | 请求过于频繁 | 降低请求频率 |
| 500 | 服务器错误 | 查看后端日志 |

---

## 请求示例

### cURL 示例

```bash
# 1. 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'

# 2. 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'

# 3. 创建对话
curl -X POST http://localhost:8000/api/conversations/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_xxx", "title": "测试", "mode": "smart_chat"}'

# 4. 发送消息
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_xxx", "conversation_id": "conv_xxx", "message": "你好"}'

# 5. 流式对话
curl -N http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_xxx", "conversation_id": "conv_xxx", "message": "你好"}'
```

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 登录
resp = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "test",
    "password": "123456"
})
user_id = resp.json()["data"]["user_id"]

# 创建对话
resp = requests.post(f"{BASE_URL}/api/conversations/create", json={
    "user_id": user_id,
    "title": "测试",
    "mode": "smart_chat"
})
conv_id = resp.json()["data"]["conversation_id"]

# 发送消息
resp = requests.post(f"{BASE_URL}/chat", json={
    "user_id": user_id,
    "conversation_id": conv_id,
    "message": "你好"
})
print(resp.json()["reply"])
```

---

## 下一步

- [架构设计](./architecture.md) - 了解系统整体架构
- [工作流详解](./workflow.md) - 深入了解 LangGraph 工作流
- [工具开发指南](./tools.md) - 学习如何添加自定义工具
