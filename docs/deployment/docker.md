# Docker 部署指南

本文档介绍如何使用 Docker 部署 LangGraph 多智能体助手。

## 前置条件

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/langgraph-agent.git
cd langgraph-agent
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```env
# 必填：LLM API 配置
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4

# 可选：RAG 嵌入模型
ZHIPUAI_API_KEY=your-zhipuai-key

# 可选：Neo4j 知识图谱
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PWD=your-neo4j-password
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 访问系统

- **前端**: http://localhost
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## 部署模式

### 基础模式（仅核心服务）

只启动前后端服务，不包含 Neo4j：

```bash
docker-compose up -d
```

### 完整模式（含知识图谱）

启动所有服务，包括 Neo4j 知识图谱：

```bash
docker-compose --profile neo4j up -d
```

### 开发模式

启动服务并挂载代码卷，方便开发调试：

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 常用命令

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f neo4j
```

### 停止服务

```bash
# 停止服务（保留数据）
docker-compose down

# 停止服务并删除数据卷
docker-compose down -v
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 重新构建

修改代码后需要重新构建镜像：

```bash
# 重新构建并启动
docker-compose up -d --build

# 只构建不启动
docker-compose build
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh
```

## 数据持久化

Docker 部署会自动创建以下数据卷：

| 卷名 | 说明 | 宿主机路径 |
|------|------|-----------|
| `chroma_data` | 向量数据库 | `./rag/chroma_db` |
| `agent_memory` | Agent 状态 | `./agent_memory` |
| `chat_history` | 对话历史 | `./chat_history` |
| `logs` | 日志文件 | `./logs` |
| `neo4j_data` | 知识图谱数据 | `./neo4j_data` |

## 配置说明

### 端口映射

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|---------|-----------|------|
| frontend | 80 | 80 | Web 界面 |
| backend | 8000 | 8000 | API 服务 |
| neo4j | 7474 | 7474 | Neo4j Browser |
| neo4j | 7687 | 7687 | Neo4j Bolt |

### 环境变量

Docker 部署支持所有 `.env` 中的环境变量，详见 [环境变量配置](../deployment/environment.md)。

### 资源限制

默认配置：

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

可根据实际情况调整。

## 生产环境部署

### 1. 使用外部数据库

生产环境建议使用外部 Neo4j 实例：

```env
# .env
NEO4J_URI=bolt://your-neo4j-server:7687
NEO4J_USER=neo4j
NEO4J_PWD=your-strong-password
```

启动时排除 Neo4j 服务：

```bash
docker-compose up -d
```

### 2. 使用反向代理

配合 Nginx 或 Traefik 使用：

```nginx
# nginx.conf
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. HTTPS 配置

使用 Let's Encrypt：

```yaml
# docker-compose.yml
services:
  frontend:
    environment:
      - VITE_API_URL=https://api.your-domain.com
```

### 4. 备份策略

定期备份数据卷：

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
docker-compose exec -T backend tar czf - /app/data > backup-$DATE.tar.gz
```

## 故障排查

### 容器无法启动

```bash
# 查看容器状态
docker-compose ps

# 查看详细日志
docker-compose logs --tail=100 backend
```

### 端口冲突

修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # 宿主机8080映射到容器8000
```

### 内存不足

调整 Docker 内存限制或增加宿主机内存：

```yaml
deploy:
  resources:
    limits:
      memory: 2G
```

### 权限问题

确保数据目录有正确权限：

```bash
sudo chown -R 1000:1000 ./logs ./rag/chroma_db
```

## 更新升级

### 更新到最新版本

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose down
docker-compose up -d --build

# 3. 清理旧镜像
docker image prune -f
```

### 数据迁移

升级前备份数据：

```bash
# 备份
tar czf backup-$(date +%Y%m%d).tar.gz ./rag ./agent_memory ./chat_history

# 升级后恢复
docker-compose down
tar xzf backup-YYYYMMDD.tar.gz
docker-compose up -d
```

## 性能优化

### 1. 使用多阶段构建

Dockerfile 已使用多阶段构建减小镜像体积。

### 2. 启用缓存

```bash
# 构建时使用缓存
docker-compose build --parallel
```

### 3. 资源限制

根据实际负载调整资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

## 监控与日志

### 查看实时日志

```bash
docker-compose logs -f --tail=100
```

### 日志轮转

Docker 默认启用日志轮转，可通过以下配置调整：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 安全建议

1. **修改默认密码**：更改 Neo4j 和 JWT 的默认密码
2. **限制端口暴露**：生产环境只暴露必要的端口
3. **使用 HTTPS**：配置 SSL 证书
4. **定期更新**：及时更新 Docker 镜像和基础镜像
5. **访问控制**：配置防火墙规则限制访问

## 下一步

- [生产环境部署](./production.md) - 生产环境最佳实践
- [环境变量详解](./environment.md) - 完整配置说明
