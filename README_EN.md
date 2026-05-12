# LangGraph Multi-Agent Assistant

English | [简体中文](./README.md)

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Vue_3-3.4-4FC08D?logo=vue.js&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-ReAct-FF6F00?logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

A multi-agent conversational system built on **LangGraph**, featuring RAG knowledge retrieval, knowledge graph reasoning, human-in-the-loop approval, multi-user management, and Plan-Execute mode. Powered by the ReAct architecture with LLM-driven tool selection across 16 built-in tools.

## Features

### 🤖 Multi-Agent Workflow (Core)

Built on the **LangGraph ReAct architecture**, enabling autonomous LLM reasoning and tool invocation:

- **ReAct Reasoning Loop**: User input → LLM reasoning → tool selection → execution → continue reasoning until final answer
- **Autonomous Tool Selection**: `llm.bind_tools()` binds 16 tools to the LLM, which independently decides when and which tools to call
- **Parallel Tool Dispatch**: LangGraph `Send` API for concurrent multi-tool execution
- **Subgraph Isolation**: Tool execution encapsulated in `tool_subgraph`, decoupled from the main Agent node
- **Self-Reflection**: `reflection_self_check` tool performs secondary validation and optimization of AI responses
- **Auto Context Compression**: Conversations exceeding 6 turns are automatically summarized, keeping the last 2 turns to prevent token overflow
- **SSE Streaming**: `graph.stream()` + Server-Sent Events for real-time output
- **State Persistence**: `SqliteSaver` disk-level persistence, recoverable across process restarts

### 📋 Plan-Execute Mode

Built on the **LangGraph Plan-Execute architecture**, enabling automatic task decomposition and execution:

- **Automatic Task Decomposition**: LLM breaks down complex problems into ordered execution steps
- **Step Execution**: Each step calls the corresponding tool and returns results
- **Dynamic Replanning**: Automatically adjusts the plan when execution fails
- **Streaming Output**: Supports SSE real-time progress updates
- **State Persistence**: Supports recovery after process restart

### 📚 Dual-Layer RAG Retrieval

- **Vector Retrieval** (ChromaDB): Document loading (TXT/MD/PDF) → RecursiveCharacterTextSplitter chunking (800 chars/chunk, 100 overlap) → Zhipu embedding-2 vectorization → similarity search (Top-K=3, score threshold 0.45)
- **Knowledge Graph** (Neo4j): Document chunking → LLM entity-relation extraction (entity1|relation|entity2|confidence) → confidence filtering → entity normalization (synonym merging) → Neo4j storage → NL-to-Cypher querying
- **LightRAG Hybrid**: local (vector RAG) / global (graph RAG) / hybrid (default) retrieval modes
- **Source Citations**: Both RAG and graph QA include document name, match score, and content snippets for traceability
- **Incremental Updates**: MD5-deduplicated incremental ChromaDB, supporting incremental/full knowledge base updates

### ✅ Human-in-the-Loop Approval

Based on **LangGraph interrupt** for workflow pause and resume:

- **High-Risk Tool Interception**: Auto-pause before `web_search`, `file_delete`, `database_write`, `file_write` execution
- **Interrupt Mechanism**: `human_approval` node in `tool_subgraph` calls `interrupt()` when high-risk tools detected, suspending the workflow
- **State Detection**: `graph.get_state(config).tasks` checks for pending interrupts
- **Workflow Resume**: After approval/rejection, `Command(resume="yes"/"no")` resumes workflow execution
- **Dual System Compatibility**: Supports both LangGraph interrupt (new) and in-memory approval queue (legacy)

### 👥 Multi-User System

- User registration/login (bcrypt secure password hashing)
- Complete data isolation between users (`thread_id = user_id`)
- Password verification required for user switching
- Forgot password / change password / delete user

### 🛡️ Production-Grade Resilience

Five-layer decorator protection chain (outer to inner):

```
global_fallback → retry → degrade → trace_log → rate_limit → core function
```

| Layer | Decorator | Purpose |
|-------|-----------|---------|
| 1st | `global_fallback` | Global fallback, returns minimal response on any exception |
| 2nd | `retry` | Auto-retry on failure (default 2 attempts) |
| 3rd | `degrade_strategy` | 3-tier degradation: search fails → local KB; RAG fails → general knowledge; dispatch fails → minimal QA |
| 4th | `agent_trace_log` | Link tracing, daily log rotation (`logs/agent-YYYY-MM-DD.log`) |
| 5th | `rate_limit` | Session-level rate limiting (1 req/sec) + idempotent dedup (same question within 3s) |

### 💬 Conversation Management

- Multi-conversation: create, switch, delete, pin, rename
- SQLite persistence (`users`, `conversations`, `messages` tables)
- 5 chat modes: smart chat, streaming chat, RAG QA, RAG streaming, real RAG streaming
- Markdown rendering + code highlighting + gradient header tables

## Agent Architecture

### ReAct Reasoning Pattern

This project adopts the **ReAct (Reasoning + Acting)** architecture, the core paradigm of Agent development:

```
Thought: What is the user asking? What information do I need?
Action: Call a tool to get information
Observation: Tool returns results
Thought: Based on results, what else do I need?
Action: Continue calling tools...
Thought: I have enough information, generate final answer
Answer: Respond to user
```

The LLM performs **reasoning** and **acting** simultaneously in each cycle until it determines a final answer can be given.

### LangGraph State Graph

```
                    ┌──────────────────────────────────┐
                    │           START                   │
                    └──────────────┬───────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │         llm_agent node            │
                    │  • Load system prompt + history   │
                    │  • LLM reasoning (tool needed?)   │
                    │  • Auto compress (>6 turns)       │
                    └──────────────┬───────────────────┘
                                   │
                          ┌────────┴────────┐
                          │   my_router     │
                          │  tool_calls?    │
                          └────────┬────────┘
                          ┌────────┴────────┐
                         Yes                No
                          │                 │
                          ▼                 ▼
              ┌─────────────────┐      ┌─────────┐
              │  tool_subgraph  │      │   END   │
              │                 │      └─────────┘
              │  ┌───────────┐  │
              │  │human_check│  │──── High-risk → interrupt()
              │  └─────┬─────┘  │         Awaiting approval
              │        ▼        │
              │  ┌───────────┐  │
              │  │ Tool Node  │  │──── Execute tool, return result
              │  └───────────┘  │
              └────────┬────────┘
                       │
                       ▼
              Back to llm_agent (continue reasoning)
```

### Tool Invocation Flow

1. **Tool Binding**: `llm.bind_tools(tools)` binds 16 tools' names, descriptions, and parameter schemas to the LLM
2. **LLM Decision**: LLM autonomously decides which tools to call based on the user's question (can call multiple in parallel)
3. **Send Dispatch**: `my_router` uses `Send` API to dispatch each tool_call to `tool_subgraph` in parallel
4. **Human Approval**: `human_approval` node checks if the tool is high-risk; if so, triggers `interrupt()` to pause
5. **Tool Execution**: After approval, `ToolNode` executes the specific tool logic
6. **Result Return**: Tool results are passed back as `ToolMessage` to `llm_agent` for continued reasoning

### Prompt Engineering

The project uses **5 system prompts** with layered design:

| Prompt | Purpose | Key Design |
|--------|---------|------------|
| `SUPERVISOR_PROMPT` | Main dispatcher | Defines 16 tool capability boundaries + invocation rules + time-sensitive keyword forced search |
| `GLOBAL_RULES` | Global constraints | No hallucination, concise output, tool utilization, no duplicate calls |
| `RAG_RETRIEVER_PROMPT` | RAG retrieval | Retrieve only, extract key query terms |
| `RAG_QA_PROMPT` | RAG QA | No hallucination + source citations + concise output |
| `KNOWLEDGE_UPDATE_PROMPT` | Knowledge update | Update only, no answering |

### Interrupt Mechanism (Human-in-the-Loop)

LangGraph's `interrupt()` is the core primitive for Human-in-the-Loop:

```python
# Key logic in workflow.py
def human_approval(state):
    """Check if tools need human approval"""
    for tool_call in state["messages"][-1].tool_calls:
        if tool_call["name"] in HIGH_RISK_TOOLS:
            interrupt({"tool_name": tool_call["name"], "args": tool_call["args"]})
    return state
```

- **Pause**: `interrupt()` raises exception, workflow state saved to SQLite
- **Detection**: `graph.get_state(config).tasks` checks for pending interrupts
- **Resume**: `graph.stream(Command(resume="yes"), config)` resumes execution

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UI Layer (Vue 3)                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐     │
│  │ LoginPage │ │ ChatPanel │ │KnowledgePnl│ │ApprovalPnl│ │PlanExecPnl│     │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘     │
│        └─────────────┴─────────────┴─────────────┴─────────────┘            │
│                                    │                                         │
│                           ┌────────┴────────┐                               │
│                           │   Pinia Store   │                               │
│                           │chat/knowledge/  │                               │
│                           │approval/planExec│                               │
│                           └────────┬────────┘                               │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ HTTP/SSE
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (FastAPI)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  /chat   │ │  /rag    │ │/knowledge│ │ /api/auth│ │/approval │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│  ┌──────────┐                                                              │
│  │/plan-exec│                                                              │
│  └────┬─────┘                                                              │
└───────┼────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent Workflow Layer (LangGraph)                      │
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                     ReAct Reasoning Loop                     │         │
│    │   ┌───────────┐    ┌───────────┐    ┌───────────┐          │         │
│    │   │ LLM Agent │───▶│  Router   │───▶│Tool Subgraph│          │         │
│    │   │ (Reason)  │◀───│(Tool Check)│   │(Exec Tools) │          │         │
│    │   └───────────┘    └───────────┘    └──────┬────┘          │         │
│    │         │              ┌───────────────────┤               │         │
│    │         │              ▼                   ▼               │         │
│    │         │      ┌─────────────┐    ┌─────────────┐         │         │
│    │         │      │Human Approval│    │  Tool Node  │         │         │
│    │         │      │ (interrupt) │    │ (Exec Tool) │         │         │
│    │         │      └─────────────┘    └─────────────┘         │         │
│    └─────────┴──────────────────────────────────────────────────┘         │
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                   Plan-Execute Mode                          │         │
│    │   ┌───────────┐    ┌───────────┐    ┌───────────┐          │         │
│    │   │  Planner  │───▶│  Executor │───▶│ Replanner │          │         │
│    │   │  (Plan)   │    │ (Execute) │    │  (Adjust) │          │         │
│    │   └───────────┘    └───────────┘    └───────────┘          │         │
│    └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│  Tools Layer   │          │ Knowledge Layer│          │ Storage Layer │
│ calculator     │          │   ChromaDB    │          │    SQLite     │
│ web_search     │          │  (Vectors)    │          │  (Users/Chat) │
│ translate      │          │   Neo4j       │          │  SqliteSaver  │
│ summary        │          │ (Graph)       │          │ (Agent State) │
│ rag_query      │          │               │          │               │
│ reflection     │          │               │          │               │
│ plan_execute   │          └───────────────┘          └───────────────┘
│     ...        │
└───────────────┘

External Services:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│     LLM     │    │  Embedding  │    │  Web Search  │
│(OpenAI API) │    │ (Zhipu AI)  │    │   (Baidu)    │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Tech Stack

| Layer | Technology | Description |
|-------|-----------|-------------|
| AI Framework | LangGraph + LangChain | Agent workflow orchestration |
| LLM | OpenAI-compatible API | Supports any OpenAI-format API |
| Vector DB | ChromaDB | Local persistent vector storage |
| Graph DB | Neo4j | Knowledge graph storage & query |
| Embedding | Zhipu AI embedding-2 | Text vectorization |
| Backend | FastAPI + Uvicorn | Async HTTP service |
| Persistence | SQLite | Users, conversations, agent state |
| Frontend | Vue 3 + Pinia | SPA interface |

## Project Structure

```
├── main.py                 # FastAPI entry point (30+ API routes)
├── workflow.py             # LangGraph workflow (ReAct + interrupt)
├── config.py               # LLM / Neo4j / high-risk tools config
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── start.sh                # One-click startup script (auto-managed venv)
├── setup.sh                # Virtual environment management script
│
├── tools/                  # 16 Agent tools
│   ├── calc_tool.py        #   Math calculator (recursive descent)
│   ├── search_tool.py      #   Web search (Baidu + LLM summary)
│   ├── translate_tool.py   #   Chinese-English translation
│   ├── summary_tool.py     #   Long text summarization
│   ├── file_tool.py        #   File operations
│   ├── rag_tools.py        #   RAG knowledge base QA
│   ├── graphrag_tool.py    #   Knowledge graph QA
│   ├── lightrag_tool.py    #   LightRAG dual-layer retrieval
│   ├── reflection_tool.py  #   Self-reflection & correction
│   ├── plan_execute_tool.py#   Plan-Execute mode
│   └── ...                 #   JSON/text/time/random tools
│
├── rag/                    # RAG retrieval module
│   ├── rag_core.py         #   Core: load→chunk→retrieve→QA→reflect→cite
│   ├── lightrag.py         #   LightRAG dual-layer retrieval
│   ├── retriever.py        #   Score-filtered retriever
│   ├── incremental_db.py   #   Incremental ChromaDB (MD5 dedup)
│   └── docs/               #   Knowledge base documents
│
├── graphrag/               # Knowledge graph module
│   ├── builder.py          #   Graph builder (docs→entities→Neo4j)
│   ├── qa.py               #   Graph QA (NL→Cypher→query)
│   ├── extractor.py        #   LLM entity-relation extraction
│   ├── entity_norm.py      #   Entity normalization
│   └── neo4j_client.py     #   Neo4j driver
│
├── plan_execute/           # Plan-Execute module
│   ├── graph.py            #   Plan-Execute workflow
│   ├── planner.py          #   Plan generator
│   ├── executor.py         #   Step executor
│   └── replanner.py        #   Dynamic replanner
│
├── prompts/
│   └── system_prompt.py    #   5 system prompts
│
├── api/
│   └── approval_api.py     #   Human approval REST API
│
├── utils/                  # Production-grade utilities
│   ├── logger.py           #   Logging (daily rotation)
│   ├── retry.py            #   Retry mechanism
│   ├── global_fallback.py  #   Global fallback
│   ├── degrade_strategy.py #   3-tier degradation
│   └── rate_limit.py       #   Rate limiting + idempotency
│
└── frontend/               # Vue 3 frontend
    └── src/
        ├── App.vue
        ├── api/index.js
        ├── stores/         #   Pinia state management
        │   ├── chat.js
        │   ├── knowledge.js
        │   ├── approval.js
        │   └── planExecute.js
        └── components/     #   Components
            ├── LoginPage.vue
            ├── ChatPanel.vue
            ├── KnowledgePanel.vue
            ├── ApprovalPanel.vue
            └── PlanExecutePanel.vue
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Neo4j 5.x (optional, for knowledge graph)

### Installation

#### Option 1: Using Virtual Environment (Recommended)

```bash
git clone https://github.com/Zhu-song/langgraph-multi-agent.git
cd langgraph-multi-agent

# Initialize virtual environment and install dependencies
./setup.sh init

# Install frontend dependencies
cd frontend && npm install && cd ..
```

#### Option 2: Global Installation

```bash
git clone https://github.com/Zhu-song/langgraph-multi-agent.git
cd langgraph-multi-agent

pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Environment Variables

```env
# LLM (OpenAI-compatible API)
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL_NAME=your-model-name
TEMPERATURE=0

# Embedding
ZHIPUAI_API_KEY=your-zhipuai-key

# Neo4j (optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PWD=your-password
```

### Run

```bash
./start.sh
# Backend http://localhost:8000  |  Frontend http://localhost:3000
```

> **Note**: `start.sh` will automatically detect and create a Python virtual environment (`venv/`), install dependencies, and start the services.

### Virtual Environment Management

The project uses Python's built-in `venv` module to manage the virtual environment, located in the `venv/` directory.

| Command | Description |
|---------|-------------|
| `./setup.sh init` | Create virtual environment and install dependencies (first time) |
| `./setup.sh install` | Install/update dependencies |
| `./setup.sh clean` | Delete virtual environment |
| `./setup.sh reset` | Reset virtual environment (delete and recreate) |
| `./setup.sh shell` | Enter virtual environment shell |

**Dependency Updates**: When `requirements.txt` is modified, the next startup will automatically detect and update dependencies.

## Docker Deployment

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Build and start
docker-compose up -d

# 3. Access
# Frontend http://localhost
# Backend http://localhost:8000
# Neo4j Console http://localhost:7474 (optional)
```

### With Neo4j Knowledge Graph

```bash
docker-compose --profile neo4j up -d
```

### Common Commands

```bash
# View logs
docker-compose logs -f

# Rebuild
docker-compose up -d --build

# Stop services
docker-compose down

# Clean data
docker-compose down -v
```

### Data Persistence

| Volume | Description |
|--------|-------------|
| `./rag/docs` | Knowledge base documents |
| `./rag/chroma_db` | Vector database |
| `./logs` | Log files |
| `agent_memory` | Agent state persistence |
| `chat_history` | Conversation history |
| `neo4j_data` | Knowledge graph data (optional) |

## Built-in Tools

| Tool | Type | Description |
|------|------|-------------|
| `calculator` | General | Safe math expression parser (recursive descent, no eval) |
| `web_search` | Search 🔴 | Baidu search + LLM summary (high-risk, requires approval) |
| `translate` | General | Chinese-English translation |
| `summary` | General | Long text summarization |
| `file_tool` | File | File create/read/write |
| `file_delete` | File 🔴 | File deletion (high-risk, requires approval) |
| `json_tool` | General | JSON formatting/validation |
| `text_stat` | Text | Word count/cleaning |
| `text_format` | Text | Case/camelCase/snake_case conversion |
| `time_tool` | General | Date/time query |
| `random_tool` | General | Random number/password/lottery |
| `rag_knowledge_query` | Knowledge | Private document RAG QA |
| `graph_knowledge_query` | Knowledge | Knowledge graph entity-relation QA |
| `lightrag_operate` | Knowledge | LightRAG dual-layer retrieval (local/global/hybrid) |
| `reflection_self_check` | Meta-cognitive | Answer self-reflection/correction |
| `incremental_rag_operate` | Knowledge | Knowledge base incremental/full update |
| `plan_execute` | Plan-Exec | Complex task decomposition and execution |

> 🔴 High-risk tools require human approval before execution

## API Endpoints

### Chat

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/chat` | Synchronous chat (supports interrupt) |
| POST | `/chat/stream` | SSE streaming chat |
| POST | `/rag` | LightRAG hybrid retrieval QA |
| POST | `/rag/stream` | LightRAG streaming output |
| POST | `/rag/real/stream` | Real RAG streaming output |

### Plan-Execute

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/plan-execute` | Plan-Execute synchronous execution |
| POST | `/plan-execute/stream` | Plan-Execute streaming execution |
| GET | `/plan-execute/status/{user_id}` | Get execution status |

### Knowledge & Approval

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/knowledge/update` | Knowledge base update |
| GET | `/api/knowledge/status` | Knowledge base status |
| POST | `/api/knowledge/graph/build` | Build knowledge graph |
| GET | `/api/approval/check/{user_id}` | Check interrupt status |
| POST | `/api/approval/resume` | Resume workflow after approval |

### User Authentication

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/verify` | Verify user password |
| POST | `/api/auth/reset-password` | Reset password |

### Conversation Management

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/history/{user_id}` | Get conversation history |
| POST | `/api/conversation/new/{user_id}` | Create new conversation |
| GET | `/api/conversation/{user_id}/{conv_id}` | Get conversation details |
| PUT | `/api/conversation/{user_id}/{conv_id}/title` | Update conversation title |
| PUT | `/api/conversation/{user_id}/{conv_id}/pinned` | Set pinned status |
| DELETE | `/api/conversation/{user_id}/{conv_id}` | Delete conversation |

## 📚 Documentation

Full documentation is available in the [docs/](./docs/README.md) directory:

| Document | Description |
|----------|-------------|
| [Installation Guide](./docs/getting-started/installation.md) | Detailed installation steps |
| [Configuration](./docs/getting-started/configuration.md) | Environment variables & config |
| [Quick Start](./docs/getting-started/quickstart.md) | Get started in 5 minutes |
| [Chat Modes](./docs/user-guide/chat-modes.md) | 5 chat modes explained |
| [Knowledge Base](./docs/user-guide/knowledge-base.md) | Build and use knowledge base |
| [Human Approval](./docs/user-guide/approval.md) | High-risk tool approval mechanism |
| [FAQ](./docs/user-guide/faq.md) | Frequently asked questions |
| [Docker Deployment](./docs/deployment/docker.md) | Deploy with Docker |
| [Production Deployment](./docs/deployment/production.md) | Production best practices |
| [Environment Variables](./docs/deployment/environment.md) | All configuration options |
| [Architecture](./docs/development/architecture.md) | System architecture design |
| [Workflow](./docs/development/workflow.md) | LangGraph workflow design |
| [Tool Development](./docs/development/tools.md) | How to add custom tools |
| [API Reference](./docs/development/api.md) | REST API documentation |
| [Contributing](./docs/contributing/contributing.md) | How to contribute |
| [Code Style](./docs/contributing/code-style.md) | Coding standards |

## Acknowledgements

Built with the following open-source projects:

| Project | Description |
|---------|-------------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Agent workflow orchestration framework |
| [LangChain](https://github.com/langchain-ai/langchain) | LLM application development framework |
| [FastAPI](https://github.com/tiangolo/fastapi) | Modern Python web framework |
| [Vue 3](https://github.com/vuejs/vue) | Progressive JavaScript framework |
| [ChromaDB](https://github.com/chroma-core/chroma) | Open-source vector database |
| [Neo4j](https://neo4j.com/) | Graph database |

## License

MIT
