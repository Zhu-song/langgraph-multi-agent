# 安装指南

本文档详细介绍 LangGraph 多智能体助手的安装步骤。

## 环境要求

- **Python**: 3.10 或更高版本
- **Node.js**: 18 或更高版本
- **操作系统**: Linux, macOS, Windows (WSL2 推荐)
- **内存**: 至少 4GB RAM
- **磁盘空间**: 至少 2GB 可用空间

## 安装方式

### 方式一：使用虚拟环境（推荐）

使用 Python 虚拟环境可以隔离项目依赖，避免与系统其他项目冲突。

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/langgraph-agent.git
cd langgraph-agent
```

#### 2. 初始化虚拟环境

```bash
./setup.sh init
```

此命令会：
- 创建 Python 虚拟环境 (`venv/`)
- 安装所有 Python 依赖
- 创建依赖安装标记文件

#### 3. 安装前端依赖

```bash
cd frontend && npm install && cd ..
```

#### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

#### 5. 启动服务

```bash
./start.sh
```

访问：
- 前端: http://localhost:3000
- 后端: http://localhost:8000

---

### 方式二：全局安装

如果你不想使用虚拟环境，可以直接全局安装。

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/langgraph-agent.git
cd langgraph-agent
```

#### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

#### 3. 安装前端依赖

```bash
cd frontend && npm install && cd ..
```

#### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

#### 5. 启动服务

```bash
./start.sh
```

---

### 方式三：Docker 安装

最简单的安装方式，无需配置本地环境。

```bash
# 1. 克隆项目
git clone https://github.com/your-username/langgraph-agent.git
cd langgraph-agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动服务
docker-compose up -d

# 4. 访问 http://localhost
```

更多 Docker 部署详情，请参考 [Docker 部署文档](../deployment/docker.md)。

## 虚拟环境管理

如果你使用虚拟环境方式安装，可以使用 `setup.sh` 管理环境：

| 命令 | 说明 |
|------|------|
| `./setup.sh init` | 创建虚拟环境并安装依赖 |
| `./setup.sh install` | 安装/更新依赖 |
| `./setup.sh clean` | 删除虚拟环境 |
| `./setup.sh reset` | 重置虚拟环境 |
| `./setup.sh shell` | 进入虚拟环境 Shell |

### 依赖更新

当 `requirements.txt` 文件更新后，运行以下命令更新依赖：

```bash
./setup.sh install
```

或者下次启动 `./start.sh` 时会自动检测并更新。

## 验证安装

启动服务后，可以通过以下方式验证安装是否成功：

### 1. 检查后端服务

```bash
curl http://localhost:8000/docs
```

应该能看到 FastAPI 的自动生成的 API 文档页面。

### 2. 检查前端服务

在浏览器中访问 http://localhost:3000，应该能看到登录页面。

### 3. 测试对话功能

1. 注册一个新用户
2. 创建对话
3. 发送测试消息，验证 AI 是否正常响应

## 常见问题

### Q: 虚拟环境创建失败？

确保已安装 `python3-venv`：

```bash
# Ubuntu/Debian
sudo apt install python3-venv

# CentOS/RHEL
sudo yum install python3-virtualenv
```

### Q: pip 安装速度慢？

使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: npm install 失败？

检查 Node.js 版本：

```bash
node --version  # 需要 v18+
```

如果版本过低，请升级 Node.js。

### Q: 端口被占用？

修改 `start.sh` 中的端口配置，或者停止占用端口的进程：

```bash
# 查找占用 8000 端口的进程
lsof -i :8000

# 杀掉进程
kill -9 <PID>
```

## 下一步

- [配置文件说明](./configuration.md) - 了解如何配置环境变量
- [5分钟快速上手](./quickstart.md) - 快速体验核心功能
