# 生产环境部署

本文档介绍如何将 LangGraph 多智能体助手部署到生产环境。

## 部署架构

### 推荐架构

```
                    ┌──────────────┐
                    │   CDN/DNS    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    Nginx     │
                    │  反向代理+SSL │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │   Frontend  │    │     │   Backend   │
       │  (静态资源)  │    │     │  (FastAPI)  │
       └─────────────┘    │     └──────┬──────┘
                          │            │
              ┌───────────┼────────────┼───────────┐
              │           │            │           │
       ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐ ┌──▼──────┐
       │  ChromaDB   │ │  Neo4j  │ │ SQLite  │ │  LLM    │
       │ (向量数据库) │ │(知识图谱)│ │ (用户数据)│ │(外部API)│
       └─────────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## 服务器要求

### 最低配置

| 资源 | 要求 |
|------|------|
| CPU | 2 核 |
| 内存 | 4GB |
| 磁盘 | 20GB SSD |
| 网络 | 5Mbps |

### 推荐配置

| 资源 | 要求 |
|------|------|
| CPU | 4 核+ |
| 内存 | 8GB+ |
| 磁盘 | 50GB SSD |
| 网络 | 10Mbps+ |

### 操作系统

- Ubuntu 22.04 LTS（推荐）
- CentOS 7+
- Debian 11+

---

## 部署步骤

### 1. 系统初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y \
    python3 python3-venv python3-pip \
    nodejs npm \
    nginx \
    git \
    curl \
    ufw

# 配置防火墙
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable
```

### 2. 部署代码

```bash
# 创建部署目录
sudo mkdir -p /opt/langgraph-agent
sudo chown $USER:$USER /opt/langgraph-agent

# 克隆代码
cd /opt/langgraph-agent
git clone https://github.com/your-username/langgraph-agent.git .

# 初始化虚拟环境
./setup.sh init

# 安装前端依赖并构建
cd frontend && npm install && npm run build && cd ..
```

### 3. 配置环境变量

```bash
# 创建生产环境配置
cp .env.example .env
vim .env
```

生产环境关键配置：

```env
# LLM
LLM_API_KEY=your-production-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
TEMPERATURE=0

# 安全
DEBUG=false
JWT_SECRET=$(openssl rand -base64 32)
JWT_EXPIRE_HOURS=8

# 日志
LOG_LEVEL=WARNING
LOG_DIR=/var/log/langgraph-agent

# 功能
ENABLE_APPROVAL=true
ENABLE_KNOWLEDGE_GRAPH=true
```

### 4. 配置 Nginx

```bash
sudo vim /etc/nginx/sites-available/langgraph-agent
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态资源
    location / {
        root /opt/langgraph-agent/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE 流式接口代理（特殊配置）
    location /chat/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /rag/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 限制上传大小
    client_max_body_size 50M;
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/langgraph-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. 配置 HTTPS（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期（Certbot 自动添加定时任务）
sudo certbot renew --dry-run
```

### 6. 配置 Systemd 服务

#### 后端服务

```bash
sudo vim /etc/systemd/system/langgraph-backend.service
```

```ini
[Unit]
Description=LangGraph Agent Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/langgraph-agent
EnvironmentFile=/opt/langgraph-agent/.env
ExecStart=/opt/langgraph-agent/venv/bin/python main.py
Restart=always
RestartSec=5

# 资源限制
MemoryMax=2G
CPUQuota=200%

# 日志
StandardOutput=append:/var/log/langgraph-agent/backend.log
StandardError=append:/var/log/langgraph-agent/backend-error.log

[Install]
WantedBy=multi-user.target
```

#### 启动服务

```bash
# 创建日志目录
sudo mkdir -p /var/log/langgraph-agent
sudo chown www-data:www-data /var/log/langgraph-agent

# 启动并设置开机自启
sudo systemctl daemon-reload
sudo systemctl enable langgraph-backend
sudo systemctl start langgraph-backend

# 查看状态
sudo systemctl status langgraph-backend
```

---

## 进阶配置

### 日志轮转

```bash
sudo vim /etc/logrotate.d/langgraph-agent
```

```
/var/log/langgraph-agent/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 www-data www-data
}
```

### 数据库备份

```bash
# 创建备份脚本
sudo vim /opt/langgraph-agent/scripts/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/langgraph-agent/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份 SQLite 数据库
cp /opt/langgraph-agent/chat_history.db $BACKUP_DIR/chat_history_$DATE.db
cp /opt/langgraph-agent/agent_memory.db $BACKUP_DIR/agent_memory_$DATE.db

# 备份知识库
tar czf $BACKUP_DIR/chroma_$DATE.tar.gz -C /opt/langgraph-agent/rag chroma_db

# 备份配置
cp /opt/langgraph-agent/.env $BACKUP_DIR/env_$DATE

# 清理 30 天前的备份
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "[$DATE] 备份完成"
```

```bash
# 添加定时任务（每天凌晨 2 点备份）
crontab -e
```

```
0 2 * * * /opt/langgraph-agent/scripts/backup.sh >> /var/log/langgraph-agent/backup.log 2>&1
```

### 性能优化

#### Uvicorn 配置

```bash
# 使用多 Worker 启动
/opt/langgraph-agent/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level warning
```

#### Nginx 优化

```nginx
# 在 http 块中添加
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
gzip_min_length 1000;

# 缓存静态资源
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    root /opt/langgraph-agent/frontend/dist;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

---

## 监控

### 健康检查

```bash
# 创建健康检查脚本
sudo vim /opt/langgraph-agent/scripts/healthcheck.sh
```

```bash
#!/bin/bash

# 检查后端服务
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)

if [ "$BACKEND_STATUS" != "200" ]; then
    echo "[$(date)] 后端服务异常，HTTP 状态码: $BACKEND_STATUS"
    systemctl restart langgraph-backend
fi
```

```bash
# 每 5 分钟检查一次
crontab -e
```

```
*/5 * * * * /opt/langgraph-agent/scripts/healthcheck.sh >> /var/log/langgraph-agent/healthcheck.log 2>&1
```

### 日志监控

```bash
# 实时查看错误日志
tail -f /var/log/langgraph-agent/backend-error.log | grep -i error

# 统计错误数量
grep -c "ERROR" /var/log/langgraph-agent/backend.log
```

---

## 安全加固

### 1. 文件权限

```bash
# 设置正确的文件权限
sudo chown -R www-data:www-data /opt/langgraph-agent
sudo chmod 600 /opt/langgraph-agent/.env
sudo chmod 700 /opt/langgraph-agent/scripts/
```

### 2. 限制访问

```nginx
# 只允许特定 IP 访问 API 文档
location /docs {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://127.0.0.1:8000;
}
```

### 3. 安全头

```nginx
# 在 server 块中添加
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

### 4. 速率限制

```nginx
# 在 http 块中添加
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

# 在 location 块中使用
location /api/ {
    limit_req zone=api burst=10 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

---

## 更新部署

### 滚动更新

```bash
#!/bin/bash
# deploy.sh - 部署更新脚本

set -e

PROJECT_DIR="/opt/langgraph-agent"
BACKUP_DIR="/opt/langgraph-agent/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "[$DATE] 开始部署更新..."

# 1. 备份
echo "备份当前版本..."
mkdir -p $BACKUP_DIR
cp $PROJECT_DIR/.env $BACKUP_DIR/env_$DATE

# 2. 拉取最新代码
echo "拉取最新代码..."
cd $PROJECT_DIR
git pull origin main

# 3. 更新后端依赖
echo "更新后端依赖..."
$PROJECT_DIR/venv/bin/pip install -r requirements.txt

# 4. 构建前端
echo "构建前端..."
cd $PROJECT_DIR/frontend && npm install && npm run build && cd ..

# 5. 重启服务
echo "重启服务..."
sudo systemctl restart langgraph-backend

# 6. 健康检查
sleep 5
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$BACKEND_STATUS" == "200" ]; then
    echo "[$DATE] 部署成功"
else
    echo "[$DATE] 部署失败，回滚中..."
    cp $BACKUP_DIR/env_$DATE $PROJECT_DIR/.env
    git checkout HEAD~1
    sudo systemctl restart langgraph-backend
    echo "[$DATE] 已回滚"
fi
```

---

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
sudo journalctl -u langgraph-backend -n 100 --no-pager

# 检查端口占用
sudo lsof -i :8000

# 检查文件权限
ls -la /opt/langgraph-agent/
```

### 502 Bad Gateway

```bash
# 检查后端是否运行
sudo systemctl status langgraph-backend

# 检查 Nginx 配置
sudo nginx -t

# 检查端口
curl http://localhost:8000/docs
```

### SSE 连接断开

```bash
# 检查 Nginx 超时配置
grep timeout /etc/nginx/sites-available/langgraph-agent

# 增加超时时间
proxy_read_timeout 300s;
```

---

## 下一步

- [Docker 部署](./docker.md) - Docker 部署方式
- [环境变量详解](./environment.md) - 完整配置说明
- [架构设计](../development/architecture.md) - 系统架构
