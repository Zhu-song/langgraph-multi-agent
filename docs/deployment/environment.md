# 环境变量详解

本文档详细介绍所有可用的环境变量配置。

## 配置概述

项目使用 `.env` 文件管理配置，支持以下配置类别：

- [LLM 配置](#llm-配置) - 大语言模型 API 设置
- [嵌入模型配置](#嵌入模型配置) - 文本向量化设置
- [Neo4j 配置](#neo4j-配置) - 知识图谱数据库
- [服务配置](#服务配置) - 服务端口和调试选项
- [日志配置](#日志配置) - 日志级别和存储
- [安全配置](#安全配置) - 认证和加密
- [功能开关](#功能开关) - 功能启用/禁用

---

## LLM 配置

### LLM_API_KEY

- **说明**: 大语言模型 API 密钥
- **必填**: 是
- **示例**: `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### LLM_BASE_URL

- **说明**: LLM API 基础 URL
- **必填**: 是
- **默认值**: `https://api.openai.com/v1`
- **支持的服务商**:
  - OpenAI: `https://api.openai.com/v1`
  - Azure: `https://your-resource.openai.azure.com/openai/deployments/your-deployment`
  - 智谱 AI: `https://open.bigmodel.cn/api/paas/v4`
  - 通义千问: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - 本地模型: `http://localhost:8000/v1`

### LLM_MODEL_NAME

- **说明**: 模型名称
- **必填**: 是
- **示例**: `gpt-4`, `glm-4`, `qwen-max`

### TEMPERATURE

- **说明**: 采样温度，控制输出随机性
- **必填**: 否
- **默认值**: `0`
- **范围**: 0-2
- **说明**: 
  - 0: 确定性输出，适合问答、计算
  - 0.7: 平衡，适合对话
  - 1.0+: 创造性输出，适合创意写作

---

## 嵌入模型配置

### ZHIPUAI_API_KEY

- **说明**: 智谱 AI API 密钥，用于文本嵌入
- **必填**: 否（但 RAG 功能需要）
- **获取方式**: [智谱 AI 开放平台](https://open.bigmodel.cn/)
- **影响功能**: RAG 知识库、向量检索

---

## Neo4j 配置

### NEO4J_URI

- **说明**: Neo4j 连接地址
- **必填**: 否
- **默认值**: `bolt://localhost:7687`
- **Docker 环境**: `bolt://neo4j:7687`

### NEO4J_USER

- **说明**: Neo4j 用户名
- **必填**: 否
- **默认值**: `neo4j`

### NEO4J_PWD

- **说明**: Neo4j 密码
- **必填**: 否
- **安全建议**: 使用强密码，至少 8 位包含字母和数字

---

## 服务配置

### BACKEND_PORT

- **说明**: 后端服务端口
- **必填**: 否
- **默认值**: `8000`
- **注意**: 修改后需要同步修改前端 API 配置

### FRONTEND_PORT

- **说明**: 前端开发服务器端口
- **必填**: 否
- **默认值**: `3000`
- **注意**: 仅开发模式有效

### DEBUG

- **说明**: 调试模式开关
- **必填**: 否
- **默认值**: `false`
- **可选值**: `true`, `false`
- **影响**: 
  - `true`: 显示详细错误信息，启用热重载
  - `false`: 生产模式，隐藏敏感信息

---

## 日志配置

### LOG_LEVEL

- **说明**: 日志级别
- **必填**: 否
- **默认值**: `INFO`
- **可选值**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### LOG_DIR

- **说明**: 日志文件存储目录
- **必填**: 否
- **默认值**: `./logs`
- **注意**: 确保目录有写入权限

---

## 安全配置

### JWT_SECRET

- **说明**: JWT 签名密钥
- **必填**: 否
- **默认值**: 随机生成（建议手动设置）
- **安全要求**: 至少 32 位随机字符串
- **生成方式**: `openssl rand -base64 32`

### JWT_EXPIRE_HOURS

- **说明**: JWT Token 过期时间
- **必填**: 否
- **默认值**: `24`
- **单位**: 小时
- **建议**: 生产环境设置较短过期时间（如 8 小时）

---

## 功能开关

### ENABLE_APPROVAL

- **说明**: 人工审核功能开关
- **必填**: 否
- **默认值**: `true`
- **可选值**: `true`, `false`
- **说明**: 控制高危工具是否需要人工审核

### ENABLE_KNOWLEDGE_GRAPH

- **说明**: 知识图谱功能开关
- **必填**: 否
- **默认值**: `true`
- **可选值**: `true`, `false`
- **说明**: 需要配置 Neo4j 才能正常使用

### ENABLE_WEB_SEARCH

- **说明**: 联网搜索功能开关
- **必填**: 否
- **默认值**: `true`
- **可选值**: `true`, `false`

---

## 完整配置示例

### 开发环境

```env
# LLM
LLM_API_KEY=sk-test-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-3.5-turbo
TEMPERATURE=0.7

# 嵌入模型
ZHIPUAI_API_KEY=test-key

# 服务
DEBUG=true
BACKEND_PORT=8000
FRONTEND_PORT=3000

# 日志
LOG_LEVEL=DEBUG

# 功能开关
ENABLE_APPROVAL=true
ENABLE_KNOWLEDGE_GRAPH=false
ENABLE_WEB_SEARCH=true
```

### 生产环境

```env
# LLM
LLM_API_KEY=sk-production-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
TEMPERATURE=0

# 嵌入模型
ZHIPUAI_API_KEY=production-key

# Neo4j
NEO4J_URI=bolt://neo4j-server:7687
NEO4J_USER=neo4j
NEO4J_PWD=strong-password-123

# 服务
DEBUG=false
BACKEND_PORT=8000

# 日志
LOG_LEVEL=WARNING
LOG_DIR=/var/log/langgraph-agent

# 安全
JWT_SECRET=your-256-bit-secret-key-here
JWT_EXPIRE_HOURS=8

# 功能开关
ENABLE_APPROVAL=true
ENABLE_KNOWLEDGE_GRAPH=true
ENABLE_WEB_SEARCH=true
```

---

## 配置优先级

环境变量加载优先级（从高到低）：

1. **系统环境变量** - `export VAR=value`
2. **.env 文件** - 项目根目录的 `.env`
3. **默认值** - 代码中的默认值

示例：

```bash
# 临时覆盖配置运行
DEBUG=true LLM_MODEL_NAME=gpt-3.5-turbo ./start.sh
```

---

## 配置验证

### 检查配置加载

启动时会输出加载的配置（敏感信息脱敏）：

```
[Config] LLM_BASE_URL: https://api.openai.com/v1
[Config] LLM_MODEL_NAME: gpt-4
[Config] DEBUG: false
```

### 测试 LLM 连接

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "hello"}'
```

### 测试 Neo4j 连接

```bash
curl http://localhost:8000/api/knowledge/graph/status
```

---

## 常见问题

### Q: 配置不生效？

1. 检查 `.env` 文件位置（必须在项目根目录）
2. 检查语法（不能有等号后面留空）
3. 重启服务
4. 检查是否有系统环境变量覆盖

### Q: 如何查看当前配置？

设置 `DEBUG=true`，启动时会打印所有配置。

### Q: 敏感信息如何保护？

1. 不要将 `.env` 文件提交到 Git
2. 使用环境变量注入（CI/CD 中）
3. 生产环境使用密钥管理服务

### Q: 多环境如何管理？

```bash
# 开发环境
cp .env.example .env.development

# 生产环境
cp .env.example .env.production

# 启动时指定
ENV_FILE=.env.production ./start.sh
```

---

## 配置参考表

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| LLM_API_KEY | 是 | - | LLM API 密钥 |
| LLM_BASE_URL | 是 | https://api.openai.com/v1 | API 基础 URL |
| LLM_MODEL_NAME | 是 | - | 模型名称 |
| TEMPERATURE | 否 | 0 | 采样温度 |
| ZHIPUAI_API_KEY | 否 | - | 智谱 AI 密钥 |
| NEO4J_URI | 否 | bolt://localhost:7687 | Neo4j 地址 |
| NEO4J_USER | 否 | neo4j | Neo4j 用户名 |
| NEO4J_PWD | 否 | - | Neo4j 密码 |
| BACKEND_PORT | 否 | 8000 | 后端端口 |
| FRONTEND_PORT | 否 | 3000 | 前端端口 |
| DEBUG | 否 | false | 调试模式 |
| LOG_LEVEL | 否 | INFO | 日志级别 |
| LOG_DIR | 否 | ./logs | 日志目录 |
| JWT_SECRET | 否 | 随机 | JWT 密钥 |
| JWT_EXPIRE_HOURS | 否 | 24 | Token 过期时间 |
| ENABLE_APPROVAL | 否 | true | 人工审核开关 |
| ENABLE_KNOWLEDGE_GRAPH | 否 | true | 知识图谱开关 |
| ENABLE_WEB_SEARCH | 否 | true | 联网搜索开关 |
