# 配置文件说明

本文档详细介绍 LangGraph 多智能体助手的所有配置选项。

## 配置文件位置

项目使用 `.env` 文件管理配置，位于项目根目录：

```
langgraph-agent/
├── .env              # 主配置文件（需要创建）
├── .env.example      # 配置示例文件
└── ...
```

## 快速开始

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

## 配置项详解

### LLM 配置（必填）

配置大语言模型 API，支持任何 OpenAI 兼容接口。

```env
# API Key
LLM_API_KEY=your-api-key-here

# API 基础 URL
LLM_BASE_URL=https://api.openai.com/v1

# 模型名称
LLM_MODEL_NAME=gpt-4

# 温度参数（0-2，越低越确定）
TEMPERATURE=0
```

**支持的模型服务商：**

| 服务商 | LLM_BASE_URL | LLM_MODEL_NAME |
|--------|--------------|----------------|
| OpenAI | https://api.openai.com/v1 | gpt-4, gpt-3.5-turbo |
| Azure | https://your-resource.openai.azure.com/openai/deployments/your-deployment | your-deployment-name |
| 智谱 AI | https://open.bigmodel.cn/api/paas/v4 | glm-4, glm-4-flash |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-max |
| 本地模型 | http://localhost:8000/v1 | 你的模型名 |

---

### 嵌入模型配置（可选）

用于 RAG 知识库的文本向量化。

```env
# 智谱 AI API Key（用于文本嵌入）
ZHIPUAI_API_KEY=your-zhipuai-api-key
```

> 注意：如果不配置，RAG 功能将无法使用。

---

### Neo4j 知识图谱配置（可选）

用于知识图谱功能，不配置则禁用该功能。

```env
# Neo4j 连接地址
NEO4J_URI=bolt://localhost:7687

# Neo4j 用户名
NEO4J_USER=neo4j

# Neo4j 密码
NEO4J_PWD=your-neo4j-password
```

**Docker 方式启动 Neo4j：**

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  neo4j:5
```

访问 http://localhost:7474 打开 Neo4j Browser。

---

### 服务配置（可选）

```env
# 后端服务端口
BACKEND_PORT=8000

# 前端服务端口
FRONTEND_PORT=3000

# 是否开启调试模式
DEBUG=false
```

---

### 日志配置（可选）

```env
# 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# 日志目录
LOG_DIR=./logs
```

---

### 安全配置（可选）

```env
# JWT 密钥（用于用户认证，请使用随机字符串）
JWT_SECRET=your-random-secret-key

# Token 过期时间（小时）
JWT_EXPIRE_HOURS=24
```

---

### 功能开关（可选）

```env
# 是否启用人工审核
ENABLE_APPROVAL=true

# 是否启用知识图谱
ENABLE_KNOWLEDGE_GRAPH=true

# 是否启用联网搜索
ENABLE_WEB_SEARCH=true
```

## 完整配置示例

```env
# ============================================
# LLM 配置（必填）
# ============================================
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
TEMPERATURE=0

# ============================================
# 嵌入模型配置（RAG 功能需要）
# ============================================
ZHIPUAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============================================
# Neo4j 知识图谱（可选）
# ============================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PWD=your-password

# ============================================
# 服务配置（可选）
# ============================================
BACKEND_PORT=8000
FRONTEND_PORT=3000
DEBUG=false

# ============================================
# 日志配置（可选）
# ============================================
LOG_LEVEL=INFO
LOG_DIR=./logs

# ============================================
# 安全配置（可选）
# ============================================
JWT_SECRET=your-random-secret-key-here
JWT_EXPIRE_HOURS=24

# ============================================
# 功能开关（可选）
# ============================================
ENABLE_APPROVAL=true
ENABLE_KNOWLEDGE_GRAPH=true
ENABLE_WEB_SEARCH=true
```

## 配置验证

启动服务后，可以通过以下方式验证配置是否正确：

### 1. 检查 LLM 配置

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "你好"}'
```

如果返回正常响应，说明 LLM 配置正确。

### 2. 检查 RAG 配置

在聊天界面选择 "RAG 问答" 模式，询问知识库相关内容。

### 3. 检查 Neo4j 配置

```bash
# 测试 Neo4j 连接
curl http://localhost:8000/api/knowledge/graph/status
```

## 环境变量优先级

配置加载优先级（从高到低）：

1. 系统环境变量
2. `.env` 文件中的变量
3. 代码中的默认值

这意味着你可以通过系统环境变量覆盖 `.env` 中的配置：

```bash
# 临时覆盖 LLM_MODEL_NAME
LLM_MODEL_NAME=gpt-3.5-turbo ./start.sh
```

## 多环境配置

如果你需要在不同环境（开发/测试/生产）使用不同配置，可以创建多个配置文件：

```bash
# 开发环境
cp .env.example .env.development

# 生产环境
cp .env.example .env.production
```

然后使用 `dotenv` 加载指定配置：

```bash
# Linux/macOS
export ENV_FILE=.env.production
./start.sh
```

## 常见问题

### Q: 配置不生效？

1. 确保 `.env` 文件位于项目根目录
2. 检查是否有语法错误（不能有等号后面留空）
3. 重启服务使配置生效

### Q: 如何查看当前配置？

在调试模式下启动，日志会打印加载的配置（敏感信息会被隐藏）。

### Q: 配置项可以留空吗？

必填项不能留空，可选功能（如 Neo4j）可以留空，对应功能会被禁用。

## 下一步

- [5分钟快速上手](./quickstart.md) - 开始体验项目功能
- [Docker 部署](../deployment/docker.md) - 使用 Docker 部署
