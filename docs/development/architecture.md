# 架构设计文档

本文档详细介绍 LangGraph 多智能体助手的系统架构设计。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层 (Vue 3)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  LoginPage  │  │  ChatPanel  │  │ KnowledgePnl│  │ApprovalPanel│        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         └────────────────┴────────────────┴────────────────┘               │
│                                   │                                          │
│                          ┌────────┴────────┐                                │
│                          │   Pinia Store   │                                │
│                          │ chat/knowledge/ │                                │
│                          │    approval     │                                │
│                          └────────┬────────┘                                │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │ HTTP/SSE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API 网关层 (FastAPI)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  /chat   │ │  /rag    │ │/knowledge│ │ /api/auth│ │/approval │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │            │                 │
└───────┼────────────┼────────────┼────────────┼────────────┼─────────────────┘
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agent 工作流层 (LangGraph)                           │
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                     ReAct 推理循环                           │         │
│    │                                                              │         │
│    │   ┌───────────┐    ┌───────────┐    ┌───────────┐          │         │
│    │   │ LLM Agent │───▶│  Router   │───▶│Tool Subgraph│          │         │
│    │   │  (推理)   │◀───│(工具判断) │    │ (执行工具)  │          │         │
│    │   └───────────┘    └───────────┘    └──────┬────┘          │         │
│    │         │                                    │               │         │
│    │         │              ┌─────────────────────┤               │         │
│    │         │              │                     │               │         │
│    │         │              ▼                     ▼               │         │
│    │         │      ┌─────────────┐      ┌─────────────┐         │         │
│    │         │      │Human Approval│      │  Tool Node  │         │         │
│    │         │      │ (interrupt) │      │ (执行工具)  │         │         │
│    │         │      └─────────────┘      └─────────────┘         │         │
│    │         │                                                    │         │
│    └─────────┴────────────────────────────────────────────────────┘         │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   工具层       │          │   知识层       │          │   存储层       │
│               │          │               │          │               │
│ ┌───────────┐ │          │ ┌───────────┐ │          │ ┌───────────┐ │
│ │calculator │ │          │ │  ChromaDB │ │          │ │  SQLite   │ │
│ │web_search │ │          │ │ (向量存储) │ │          │ │(用户/对话)│ │
│ │translate  │ │          │ └───────────┘ │          │ └───────────┘ │
│ │summary    │ │          │ ┌───────────┐ │          │ ┌───────────┐ │
│ │file_tool  │ │          │ │   Neo4j   │ │          │ │SqliteSaver│ │
│ │rag_query  │ │          │ │(知识图谱) │ │          │ │(Agent状态)│ │
│ │reflection │ │          │ └───────────┘ │          │ └───────────┘ │
│ │    ...    │ │          │               │          │               │
│ └───────────┘ │          └───────────────┘          └───────────────┘
└───────────────┘

外部服务:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│     LLM     │    │  Embedding  │    │   百度搜索   │
│ (OpenAI兼容)│    │  (智谱AI)   │    │   (联网)    │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 分层架构

### 1. 用户界面层 (Presentation Layer)

**技术栈**: Vue 3 + Pinia + Element Plus

**职责**:
- 用户交互界面渲染
- 状态管理（Pinia Store）
- API 请求封装
- 实时消息处理（SSE）

**核心组件**:
```
frontend/src/
├── components/
│   ├── LoginPanel.vue      # 登录/注册
│   ├── ChatPanel.vue       # 对话界面
│   ├── KnowledgePanel.vue  # 知识库管理
│   └── ApprovalPanel.vue   # 人工审核
├── stores/
│   ├── chat.js             # 对话状态
│   ├── knowledge.js        # 知识库状态
│   └── approval.js         # 审核状态
└── api/
    └── index.js            # API 封装
```

### 2. API 网关层 (API Gateway)

**技术栈**: FastAPI + Uvicorn

**职责**:
- HTTP 请求路由
- 请求/响应序列化
- 认证鉴权
- CORS 跨域处理
- 全局异常处理

**核心模块**:
```
main.py
├── /chat                 # 对话接口
├── /chat/stream          # 流式对话
├── /rag                  # RAG 问答
├── /knowledge            # 知识库管理
├── /api/auth             # 用户认证
└── /api/approval         # 人工审核
```

### 3. Agent 工作流层 (Agent Workflow)

**技术栈**: LangGraph + LangChain

**职责**:
- ReAct 推理循环
- 工具调用管理
- 人工审核集成
- 状态持久化

**核心组件**:
```
workflow.py
├── StateGraph            # 状态图定义
├── llm_agent             # LLM 推理节点
├── my_router             # 路由判断
├── tool_subgraph         # 工具执行子图
│   ├── human_approval    # 人工审核节点
│   └── ToolNode          # 工具执行节点
└── SqliteSaver           # 状态持久化
```

### 4. 工具层 (Tools Layer)

**职责**:
- 15 种内置工具实现
- 工具注册与发现
- 工具执行隔离

**工具分类**:
```
tools/
├── calc_tool.py          # 数学计算
├── search_tool.py        # 联网搜索
├── translate_tool.py     # 翻译
├── summary_tool.py       # 摘要
├── file_tool.py          # 文件操作
├── rag_tools.py          # RAG 查询
├── graphrag_tool.py      # 知识图谱
└── ...
```

### 5. 知识层 (Knowledge Layer)

**技术栈**: ChromaDB + Neo4j

**职责**:
- 向量存储与检索
- 知识图谱构建与查询
- 文档处理与索引

**核心模块**:
```
rag/
├── rag_core.py           # RAG 核心逻辑
├── lightrag.py           # LightRAG 实现
├── incremental_db.py     # 增量索引
└── docs/                 # 文档存储

graphrag/
├── builder.py            # 图谱构建
├── qa.py                 # 图谱问答
├── extractor.py          # 实体抽取
└── neo4j_client.py       # Neo4j 客户端
```

### 6. 存储层 (Storage Layer)

**技术栈**: SQLite

**职责**:
- 用户数据持久化
- 对话历史存储
- Agent 状态保存

**数据模型**:
```sql
-- 用户表
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    created_at TIMESTAMP
);

-- 对话表
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    mode TEXT,
    created_at TIMESTAMP
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    created_at TIMESTAMP
);
```

## 核心流程

### 对话流程

```
用户输入
    ↓
前端发送 POST /chat/stream
    ↓
FastAPI 接收请求
    ↓
创建 LangGraph 配置 (thread_id = user_id)
    ↓
graph.stream() 启动工作流
    ↓
llm_agent 节点：LLM 推理
    ↓
my_router 判断：是否需要工具？
    ├─ 否 → 直接生成回答 → SSE 流式输出
    ↓
    是
    ↓
tool_subgraph 并行执行工具
    ↓
human_approval 检查：是否高危工具？
    ├─ 是 → interrupt() 暂停 → 等待人工审核
    ├─ 否 → 直接执行
    ↓
ToolNode 执行工具
    ↓
返回工具结果到 llm_agent
    ↓
LLM 基于工具结果生成回答
    ↓
SSE 流式输出到前端
```

### RAG 流程

```
用户提问 (RAG 模式)
    ↓
检索知识库 (ChromaDB)
    ↓
获取 Top-K 相关文档片段
    ↓
构建 Prompt：系统提示 + 上下文 + 问题
    ↓
LLM 生成回答
    ↓
附加来源引用
    ↓
返回完整回答
```

### 人工审核流程

```
LLM 决定调用高危工具 (如 web_search)
    ↓
interrupt({tool_name, args}) 抛出中断
    ↓
工作流状态保存到 SQLite
    ↓
前端轮询 /api/approval/check
    ↓
显示审核请求在 ApprovalPanel
    ↓
管理员选择 通过/拒绝
    ↓
POST /api/approval/resume
    ↓
Command(resume="yes"/"no") 恢复工作流
    ↓
继续执行或返回拒绝信息
```

## 数据流

### 请求数据流

```
Browser → HTTP Request → Nginx (可选)
    ↓
FastAPI Router
    ↓
Pydantic Model Validation
    ↓
Service/Agent Layer
    ↓
Database/External API
    ↓
Response → JSON/SSE → Browser
```

### 状态数据流

```
LangGraph State
    ↓
SqliteSaver (checkpoint)
    ↓
SQLite Database
    ↓
Disk Storage
```

## 安全设计

### 认证鉴权

```
用户登录
    ↓
验证用户名密码 (SHA256)
    ↓
生成 JWT Token
    ↓
前端存储 Token
    ↓
后续请求携带 Token
    ↓
后端验证 Token 有效性
```

### 数据隔离

```
用户 A (thread_id = user_a)
    ↓
只能访问自己的对话历史
    ↓
只能访问自己的知识库
    ↓
只能处理自己的审核请求
```

### 人工审核

```
高危工具调用
    ↓
自动触发审核流程
    ↓
等待人工批准
    ↓
审计日志记录
```

## 扩展性设计

### 水平扩展

```
Load Balancer
    ├── Backend Instance 1
    ├── Backend Instance 2
    └── Backend Instance N
    
共享存储:
    - SQLite (可替换为 PostgreSQL)
    - ChromaDB (可替换为向量数据库服务)
    - Neo4j (独立集群)
```

### 垂直扩展

- **模型升级**: 支持更换更强的 LLM
- **工具扩展**: 动态注册新工具
- **知识库扩展**: 支持多种数据源

## 性能优化

### 缓存策略

```
Client Cache
    - 对话列表
    - 用户配置
    
API Cache
    - 知识库状态
    - 工具元数据
    
Database Cache
    - 热点查询结果
```

### 异步处理

```
同步操作:
    - 对话请求
    - 用户认证
    
异步操作:
    - 知识库索引
    - 知识图谱构建
    - 日志写入
```

## 监控与日志

### 日志分层

```
Application Log
    - 请求/响应
    - 错误堆栈
    
Agent Log
    - 推理过程
    - 工具调用
    
Audit Log
    - 用户操作
    - 审核记录
```

### 监控指标

```
系统指标:
    - QPS
    - 响应时间
    - 错误率
    
业务指标:
    - 对话数
    - 工具调用次数
    - 审核通过率
```

## 下一步

- [工作流详解](./workflow.md) - 深入了解 LangGraph 工作流
- [工具开发指南](./tools.md) - 学习如何添加自定义工具
- [API 接口文档](./api.md) - 查看 REST API 详情
