# LangGraph 多智能体助手

[English](./README_EN.md) | 简体中文

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Vue_3-3.4-4FC08D?logo=vue.js&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-ReAct-FF6F00?logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

基于 **LangGraph** 的多智能体对话系统，集成 RAG 知识库检索、知识图谱推理、人工审核、多用户管理等功能。采用 ReAct 架构，LLM 自主决策工具调用，支持 15 种内置工具。

## 功能特性

### 🤖 多智能体工作流（核心）

基于 **LangGraph ReAct 架构**，实现 LLM 自主推理与工具调用循环：

- **ReAct 推理循环**：LLM 接收用户输入 → 推理是否需要工具 → 调用工具 → 获取结果 → 继续推理，直到生成最终答案
- **工具自主决策**：通过 `llm.bind_tools()` 将 15 种工具绑定到 LLM，由模型自主判断何时调用哪个工具
- **并行工具派发**：使用 LangGraph `Send` API 实现多工具并行执行
- **子图隔离**：工具执行封装在 `tool_subgraph` 子图中，与主 Agent 节点解耦
- **自省纠错机制**：`reflection_self_check` 工具对 AI 回答进行二次校验与优化
- **长对话自动压缩**：超过 6 轮自动总结历史，保留最近 2 轮，防止 Token 溢出
- **SSE 流式输出**：`graph.stream()` + Server-Sent Events 实时推送
- **状态持久化**：`SqliteSaver` 硬盘级持久化，进程重启可恢复会话

### 📚 双层 RAG 检索

- **向量检索**（ChromaDB）：文档加载（TXT/MD/PDF）→ RecursiveCharacterTextSplitter 分块（800字符/块，100重叠）→ 智谱 embedding-2 向量化 → 相似度检索（Top-K=3，分数阈值 0.45）
- **知识图谱**（Neo4j）：文档分块 → LLM 实体关系抽取（实体1|关系|实体2|置信度）→ 置信度过滤 → 实体归一化（同义词合并）→ Neo4j 写入 → 自然语言转 Cypher 查询
- **LightRAG 双层混合**：local（向量 RAG）/ global（图谱 RAG）/ hybrid（混合，默认）三种检索模式
- **来源引用**：RAG 和图谱问答均附带文档名、匹配度、内容片段等可溯源引用
- **增量更新**：MD5 去重的增量式 ChromaDB，支持增量/全量知识库更新

### ✅ 人工审核机制（Human-in-the-Loop）

基于 **LangGraph interrupt** 实现工作流暂停与恢复：

- **高危工具拦截**：`web_search`、`file_delete`、`database_write`、`file_write` 等工具触发前自动暂停
- **interrupt 机制**：`tool_subgraph` 中的 `human_approval` 节点检测到高危工具时调用 `interrupt()`，工作流挂起
- **状态检测**：通过 `graph.get_state(config).tasks` 检查是否存在未处理的 interrupt
- **恢复执行**：审核通过/拒绝后，通过 `Command(resume="yes"/"no")` 恢复工作流继续执行
- **双系统兼容**：同时支持 LangGraph interrupt（新）和内存审核队列（旧）两套审核系统

### 👥 多用户系统

- 用户注册/登录（bcrypt 安全密码哈希）
- 用户间数据完全隔离（`thread_id = user_id`）
- 用户切换需密码验证
- 忘记密码 / 修改密码 / 删除用户

### 🛡️ 生产级健壮性

五层装饰器保护链（由外到内）：

```
global_fallback → retry → degrade → trace_log → rate_limit → 核心函数
```

| 层级 | 装饰器 | 作用 |
|------|--------|------|
| 第 1 层 | `global_fallback` | 全局兜底，任何异常返回极简通用回答 |
| 第 2 层 | `retry` | 失败自动重试（默认 2 次） |
| 第 3 层 | `degrade_strategy` | 三级降级：搜索失败→本地知识库；RAG 失败→通用常识；调度异常→极简问答 |
| 第 4 层 | `agent_trace_log` | 链路日志，按天文件切割（`logs/agent-YYYY-MM-DD.log`） |
| 第 5 层 | `rate_limit` | 会话级限流（1秒/请求）+ 幂等防重复（3秒内相同问题） |

### 💬 对话管理

- 多对话：新建、切换、删除、置顶、重命名
- SQLite 持久化（`users`、`conversations`、`messages` 三张表）
- 5 种对话模式：智能对话、流式对话、RAG 问答、RAG 流式、真实 RAG 流式
- Markdown 渲染 + 代码高亮 + 渐变表头表格

## Agent 架构详解

### ReAct 推理模式

本项目采用 **ReAct（Reasoning + Acting）** 架构，是 Agent 开发的核心范式：

```
Thought: 用户问的是什么？我需要什么信息？
Action: 调用工具获取信息
Observation: 工具返回结果
Thought: 根据结果，我还需要什么？
Action: 继续调用工具...
Thought: 我有足够信息了，生成最终回答
Answer: 最终回答用户
```

LLM 在每一轮循环中同时进行**推理（Reasoning）**和**行动（Acting）**，直到判断可以给出最终答案。

### LangGraph 状态图

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

### 工具调用流程

1. **工具绑定**：`llm.bind_tools(tools)` 将 15 个工具的名称、描述、参数 schema 绑定到 LLM
2. **LLM 决策**：LLM 根据用户问题和可用工具，自主决定调用哪些工具（可并行调用多个）
3. **Send 派发**：`my_router` 使用 `Send` API 将每个 tool_call 并行派发到 `tool_subgraph`
4. **人工审批**：`human_approval` 节点检查工具是否为高危工具，是则触发 `interrupt()` 暂停
5. **工具执行**：通过审批后，`ToolNode` 执行具体工具逻辑
6. **结果回传**：工具结果作为 `ToolMessage` 回到 `llm_agent`，LLM 继续推理

### 提示词工程

项目使用 **5 套系统提示词**，分层设计：

| 提示词 | 用途 | 关键设计 |
|--------|------|----------|
| `SUPERVISOR_PROMPT` | 总调度器 | 定义 15 种工具能力边界 + 调用规则 + 时效性关键词强制搜索 |
| `GLOBAL_RULES` | 全局约束 | 禁止幻觉、简洁输出、善用工具、不重复调用 |
| `RAG_RETRIEVER_PROMPT` | RAG 检索 | 只检索不生成，提取关键查询词 |
| `RAG_QA_PROMPT` | RAG 问答 | 禁止幻觉 + 来源引用 + 简洁输出 |
| `KNOWLEDGE_UPDATE_PROMPT` | 知识更新 | 只做更新不回答 |

### Interrupt 机制（人工审核）

LangGraph 的 `interrupt()` 是实现 Human-in-the-Loop 的核心原语：

```python
# workflow.py 中的关键逻辑
def human_approval(state):
    """检查工具是否需要人工审批"""
    for tool_call in state["messages"][-1].tool_calls:
        if tool_call["name"] in HIGH_RISK_TOOLS:
            interrupt({"tool_name": tool_call["name"], "args": tool_call["args"]})
    return state
```

- **暂停**：`interrupt()` 抛出异常，工作流状态保存到 SQLite
- **检测**：`graph.get_state(config).tasks` 检查是否有未处理的 interrupt
- **恢复**：`graph.stream(Command(resume="yes"), config)` 恢复执行

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层 (Vue 3)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  LoginPage  │  │  ChatPanel  │  │ KnowledgePnl│  │ApprovalPanel│        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
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

### 数据流

```
用户提问
    │
    ▼
┌─────────────┐
│  前端发送   │ ──── POST /chat/stream ────▶
└─────────────┘
    │
    ▼
┌─────────────┐
│ FastAPI接收 │ ──── 创建 LangGraph 配置 ────▶
└─────────────┘
    │
    ▼
┌─────────────┐
│ LLM 推理    │ ◀─── 加载系统提示词 + 对话历史
└─────────────┘
    │
    ├── 无需工具 ──▶ SSE 流式返回答案
    │
    └── 需要工具
         │
         ▼
    ┌─────────────┐
    │ 高危工具?   │
    └─────────────┘
         │
    ┌────┴────┐
    │         │
   Yes        No
    │         │
    ▼         ▼
┌─────────┐ ┌─────────┐
│interrupt│ │执行工具 │
│等待审核 │ └────┬────┘
└────┬────┘      │
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│人工审核 │ │工具结果 │
│通过/拒绝│ │回传 LLM │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
    ┌─────────────┐
    │ LLM 继续推理 │
    └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ SSE 流式输出 │ ──── 前端实时渲染 ────▶ 用户看到答案
    └─────────────┘
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| AI 框架 | LangGraph + LangChain | Agent 工作流编排 |
| LLM | OpenAI 兼容接口 | 支持任何 OpenAI 格式 API |
| 向量数据库 | ChromaDB | 本地持久化向量存储 |
| 图数据库 | Neo4j | 知识图谱存储与查询 |
| 嵌入模型 | 智谱 AI embedding-2 | 文本向量化 |
| 后端框架 | FastAPI + Uvicorn | 异步 HTTP 服务 |
| 数据持久化 | SQLite | 用户、对话、Agent 状态 |
| 前端 | Vue 3 + Pinia | SPA 界面 |

## 项目结构

```
├── main.py                 # FastAPI 主入口（26 个 API 路由）
├── workflow.py             # LangGraph 工作流（ReAct + interrupt）
├── config.py               # LLM / Neo4j 配置
├── .env                    # 环境变量
├── requirements.txt        # Python 依赖
├── start.sh                # 一键启动脚本（自动管理虚拟环境）
├── setup.sh                # 虚拟环境管理脚本
│
├── tools/                  # 15 个 Agent 工具
│   ├── calc_tool.py        #   数学计算器（递归下降解析）
│   ├── search_tool.py      #   联网搜索（百度 + LLM 总结）
│   ├── translate_tool.py   #   中英翻译
│   ├── summary_tool.py     #   长文本摘要
│   ├── file_tool.py        #   文件操作
│   ├── rag_tools.py        #   RAG 知识库问答
│   ├── graphrag_tool.py    #   知识图谱问答
│   ├── lightrag_tool.py    #   LightRAG 双层检索
│   ├── reflection_tool.py  #   自省纠错
│   └── ...                 #   JSON/文本/时间/随机数等
│
├── rag/                    # RAG 检索模块
│   ├── rag_core.py         #   核心：加载→分块→检索→问答→自省→引用
│   ├── lightrag.py         #   LightRAG 双层检索类
│   ├── retriever.py        #   带分数过滤的检索器
│   ├── incremental_db.py   #   增量式 ChromaDB（MD5 去重）
│   └── docs/               #   知识库文档目录
│
├── graphrag/               # 知识图谱模块
│   ├── builder.py          #   图谱构建（文档→实体关系→Neo4j）
│   ├── qa.py               #   图谱问答（NL→Cypher→查询）
│   ├── extractor.py        #   LLM 实体关系抽取
│   ├── entity_norm.py      #   实体归一化
│   └── neo4j_client.py     #   Neo4j 驱动
│
├── prompts/
│   └── system_prompt.py    #   5 套系统提示词
│
├── api/
│   └── approval_api.py     #   人工审核 REST API
│
├── utils/                  # 生产级工具包
│   ├── logger.py           #   日志（按天切割）
│   ├── retry.py            #   重试
│   ├── global_fallback.py  #   全局兜底
│   ├── degrade_strategy.py #   三级降级
│   └── rate_limit.py       #   限流 + 幂等
│
└── frontend/               # Vue 3 前端
    └── src/
        ├── App.vue
        ├── api/index.js
        ├── stores/         #   Pinia 状态管理
        └── components/     #   登录/聊天/知识库/审核
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Neo4j 5.x（可选，知识图谱功能需要）

### 安装

#### 方式一：使用虚拟环境（推荐）

```bash
git clone https://github.com/your-username/langgraph-agent.git
cd langgraph-agent

# 初始化虚拟环境并安装依赖
./setup.sh init

# 安装前端依赖
cd frontend && npm install && cd ..
```

#### 方式二：全局安装

```bash
git clone https://github.com/Zhu-song/langgraph-agent.git
cd langgraph-agent

pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 环境变量

```env
# LLM（OpenAI 兼容接口）
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL_NAME=your-model-name
TEMPERATURE=0

# 嵌入模型
ZHIPUAI_API_KEY=your-zhipuai-key

# Neo4j（可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PWD=your-password
```

### 启动

```bash
./start.sh
# 后端 http://localhost:8000  |  前端 http://localhost:3000
```

> **注意**：`start.sh` 会自动检测并创建 Python 虚拟环境（`venv/`），自动安装依赖，然后启动服务。

### 虚拟环境管理

项目使用 Python 内置的 `venv` 模块管理虚拟环境，位于 `venv/` 目录。

| 命令 | 说明 |
|------|------|
| `./setup.sh init` | 创建虚拟环境并安装依赖（首次使用） |
| `./setup.sh install` | 安装/更新依赖 |
| `./setup.sh clean` | 删除虚拟环境 |
| `./setup.sh reset` | 重置虚拟环境（删除后重新创建） |
| `./setup.sh shell` | 进入虚拟环境 Shell |

**依赖更新**：当 `requirements.txt` 修改后，下次启动时会自动检测并更新依赖。

## Docker 部署

### 快速启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. 构建并启动
docker-compose up -d

# 3. 访问
# 前端 http://localhost
# 后端 http://localhost:8000
# Neo4j 控制台 http://localhost:7474（可选）
```

### 包含 Neo4j 知识图谱

```bash
docker-compose --profile neo4j up -d
```

### 常用命令

```bash
# 查看日志
docker-compose logs -f

# 重新构建
docker-compose up -d --build

# 停止服务
docker-compose down

# 清理数据
docker-compose down -v
```

### 数据持久化

| 目录 | 说明 |
|------|------|
| `./rag/docs` | 知识库文档 |
| `./rag/chroma_db` | 向量数据库 |
| `./logs` | 日志文件 |
| `agent_memory` | Agent 状态持久化 |
| `chat_history` | 对话历史 |
| `neo4j_data` | 知识图谱数据（可选） |

## 内置工具

| 工具 | 类型 | 说明 |
|------|------|------|
| `calculator` | 通用 | 安全数学表达式解析（递归下降，非 eval） |
| `web_search` | 搜索 🔴 | 百度搜索 + LLM 精炼总结（高危，需审核） |
| `translate` | 通用 | 中英文互译 |
| `summary` | 通用 | 长文本摘要总结 |
| `file_tool` | 文件 | 文件创建/读取/写入 |
| `file_delete` | 文件 🔴 | 文件删除（高危，需审核） |
| `json_tool` | 通用 | JSON 格式化/校验 |
| `text_stat` | 文本 | 字数统计/清洗 |
| `text_format` | 文本 | 大小写/驼峰/下划线转换 |
| `time_tool` | 通用 | 时间日期查询 |
| `random_tool` | 通用 | 随机数/密码/抽签 |
| `rag_knowledge_query` | 知识库 | 私有文档 RAG 问答 |
| `graph_knowledge_query` | 知识库 | 知识图谱实体关系问答 |
| `lightrag_operate` | 知识库 | LightRAG 双层检索（local/global/hybrid） |
| `reflection_self_check` | 元认知 | 答案自省纠错/润色 |
| `incremental_rag_operate` | 知识库 | 知识库增量/全量更新 |

> 🔴 标记为高危工具，调用前需人工审核通过

## API 接口

### 对话

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/chat` | 普通对话（同步，支持 interrupt） |
| POST | `/chat/stream` | SSE 流式对话 |
| POST | `/rag` | LightRAG 混合检索问答 |
| POST | `/rag/stream` | LightRAG 流式输出 |
| POST | `/rag/real/stream` | 真实 RAG 流式输出 |

### 知识库 & 审核

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/knowledge/update` | 知识库更新 |
| GET | `/api/knowledge/status` | 知识库状态 |
| POST | `/api/knowledge/graph/build` | 构建知识图谱 |
| GET | `/api/approval/check/{user_id}` | 检查 interrupt 状态 |
| POST | `/api/approval/resume` | 审核后恢复工作流 |

## 📚 文档

完整文档请访问 [docs/](./docs/README.md) 目录：

| 文档 | 说明 |
|------|------|
| [安装指南](./docs/getting-started/installation.md) | 详细的安装步骤 |
| [配置文件说明](./docs/getting-started/configuration.md) | 环境变量与配置详解 |
| [5分钟快速上手](./docs/getting-started/quickstart.md) | 快速体验核心功能 |
| [对话模式说明](./docs/user-guide/chat-modes.md) | 5种对话模式的区别与使用 |
| [知识库使用指南](./docs/user-guide/knowledge-base.md) | 如何构建和使用知识库 |
| [人工审核功能](./docs/user-guide/approval.md) | 高危工具的人工审核机制 |
| [常见问题 FAQ](./docs/user-guide/faq.md) | 常见问题解答 |
| [Docker 部署](./docs/deployment/docker.md) | 使用 Docker 快速部署 |
| [生产环境部署](./docs/deployment/production.md) | 生产环境最佳实践 |
| [环境变量详解](./docs/deployment/environment.md) | 所有配置项说明 |
| [架构设计](./docs/development/architecture.md) | 系统架构详解 |
| [工作流详解](./docs/development/workflow.md) | LangGraph 工作流设计 |
| [工具开发指南](./docs/development/tools.md) | 如何添加自定义工具 |
| [API 接口文档](./docs/development/api.md) | REST API 详细说明 |
| [贡献指南](./docs/contributing/contributing.md) | 如何参与项目贡献 |
| [代码规范](./docs/contributing/code-style.md) | 编码规范与风格 |

## 致谢

本项目基于以下开源项目构建：

| 项目 | 说明 |
|------|------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Agent 工作流编排框架 |
| [LangChain](https://github.com/langchain-ai/langchain) | LLM 应用开发框架 |
| [FastAPI](https://github.com/tiangolo/fastapi) | 现代 Python Web 框架 |
| [Vue 3](https://github.com/vuejs/vue) | 渐进式 JavaScript 框架 |
| [ChromaDB](https://github.com/chroma-core/chroma) | 开源向量数据库 |
| [Neo4j](https://neo4j.com/) | 图数据库 |

感谢开源社区的贡献！

## License

MIT
