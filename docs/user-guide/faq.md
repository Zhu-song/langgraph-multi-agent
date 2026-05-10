# 常见问题 FAQ

本文档汇总了使用 LangGraph 多智能体助手时的常见问题及解决方法。

## 快速导航

- [安装部署问题](#安装部署问题)
- [配置问题](#配置问题)
- [对话功能问题](#对话功能问题)
- [知识库问题](#知识库问题)
- [人工审核问题](#人工审核问题)
- [性能问题](#性能问题)
- [其他问题](#其他问题)

---

## 安装部署问题

> 💡 **详细安装指南**: [安装指南](./installation.md) | [Docker 部署](../deployment/docker.md)

### Q: 虚拟环境创建失败？

**错误信息**: `Error: [Errno 2] No such file or directory: 'python3'`

**解决方法**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-pip

# CentOS/RHEL
sudo yum install python3 python3-virtualenv

# macOS
brew install python3
```

### Q: pip 安装依赖时超时？

**解决方法**:
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者使用阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### Q: npm install 报错？

**错误信息**: `npm ERR! code EACCES`

**解决方法**:
```bash
# 方法1：使用 npx
npx npm install

# 方法2：修改 npm 权限
sudo chown -R $(whoami) ~/.npm

# 方法3：使用 cnpm
npm install -g cnpm --registry=https://registry.npm.taobao.org
cnpm install
```

### Q: Docker 启动失败？

**错误信息**: `Error response from daemon: Ports are not available`

**解决方法**:
```bash
# 查看端口占用
sudo lsof -i :8000
sudo lsof -i :3000

# 杀掉占用进程
kill -9 <PID>

# 或者修改 docker-compose.yml 中的端口映射
```

---

## 配置问题

> 💡 **详细配置说明**: [配置文件说明](../getting-started/configuration.md) | [环境变量详解](../deployment/environment.md)

### Q: 配置不生效？

**检查清单**:
1. `.env` 文件是否在项目根目录
2. 配置项格式是否正确（`KEY=value`，无空格）
3. 是否重启了服务
4. 是否有系统环境变量覆盖

**调试方法**:
```bash
# 设置 DEBUG 模式查看加载的配置
DEBUG=true ./start.sh
```

### Q: LLM API 连接失败？

**错误信息**: `Error: Connection error` 或 `401 Unauthorized`

**解决方法**:
1. 检查 `LLM_API_KEY` 是否正确
2. 检查 `LLM_BASE_URL` 是否包含 `/v1` 后缀
3. 检查网络是否能访问 API 地址
4. 确认 API Key 有余额且未过期

```bash
# 测试 API 连接
curl $LLM_BASE_URL/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

### Q: Neo4j 连接失败？

**错误信息**: `Failed to establish connection to Neo4j`

**解决方法**:
1. 确认 Neo4j 服务已启动
2. 检查 `NEO4J_URI` 配置（Docker 环境使用 `bolt://neo4j:7687`）
3. 检查用户名密码是否正确
4. 检查防火墙是否放行 7687 端口

---

## 对话功能问题

> 💡 **详细使用指南**: [对话模式说明](./chat-modes.md)

### Q: AI 不调用工具？

**可能原因**:
1. 使用了不支持工具调用的模式（RAG 模式）
2. 问题描述不够明确，AI 判断不需要工具
3. 工具配置有问题

**解决方法**:
1. 切换到"智能对话"或"流式对话"模式
2. 明确表达需要使用工具：
   ```
   请使用计算器计算：123 * 456
   ```
3. 检查工具是否已正确注册

### Q: 流式输出卡顿？

**可能原因**:
1. 网络延迟
2. LLM 响应慢
3. 前端渲染问题

**解决方法**:
1. 检查网络连接
2. 更换更快的 LLM 服务商
3. 刷新页面或更换浏览器
4. 切换到非流式模式

### Q: 对话历史丢失？

**可能原因**:
1. 使用了隐私/无痕模式
2. 清除了浏览器数据
3. 数据库文件损坏

**解决方法**:
1. 使用普通模式浏览
2. 检查 `chat_history` 目录权限
3. 查看后端日志是否有数据库错误

### Q: 无法创建新对话？

**可能原因**:
1. 未登录或登录已过期
2. 数据库锁定
3. 前端缓存问题

**解决方法**:
1. 重新登录
2. 重启后端服务
3. 清除浏览器缓存

---

## 知识库问题

### Q: RAG 回答不准确？

**可能原因**:
1. 文档未成功索引
2. 问题与文档内容不相关
3. 检索阈值设置不当

**解决方法**:
1. 检查知识库状态，重新执行"更新知识库"
2. 使用文档中的关键词提问
3. 检查文档是否包含答案
4. 尝试调整提问方式

### Q: 文档上传失败？

**可能原因**:
1. 文件格式不支持
2. 文件过大（> 50MB）
3. 文件名包含特殊字符
4. 磁盘空间不足

**解决方法**:
1. 转换为支持的格式（TXT、MD、PDF）
2. 压缩或分割大文件
3. 重命名文件（使用英文、数字、下划线）
4. 检查磁盘空间

### Q: 索引更新卡住？

**可能原因**:
1. 智谱 AI API Key 无效
2. 网络连接问题
3. 文档内容为空或损坏

**解决方法**:
1. 检查 `ZHIPUAI_API_KEY` 配置
2. 检查网络连接
3. 删除问题文档重新上传
4. 查看后端日志获取详细错误信息

### Q: 知识图谱无法使用？

**可能原因**:
1. Neo4j 未配置
2. `ENABLE_KNOWLEDGE_GRAPH` 设置为 false
3. 未构建知识图谱

**解决方法**:
1. 配置 Neo4j 连接信息
2. 设置 `ENABLE_KNOWLEDGE_GRAPH=true`
3. 点击"构建知识图谱"按钮
4. 检查 Neo4j 服务状态

---

## 人工审核问题

> 💡 **详细功能说明**: [人工审核功能](./approval.md)

### Q: 审核面板不显示请求？

**可能原因**:
1. `ENABLE_APPROVAL` 设置为 false
2. 没有触发高危工具
3. 审核请求已过期

**解决方法**:
1. 检查 `.env` 中的 `ENABLE_APPROVAL=true`
2. 尝试触发高危工具（如搜索）
3. 检查审核超时设置

### Q: 审核通过后无响应？

**可能原因**:
1. 工具执行失败
2. 网络连接问题
3. 工作流状态异常

**解决方法**:
1. 查看后端日志
2. 检查工具配置
3. 重启服务
4. 重新触发审核流程

### Q: 如何禁用人工审核？

**注意**: 仅建议开发环境使用

```env
# .env
ENABLE_APPROVAL=false
```

生产环境强烈建议保持启用。

---

## 性能问题

### Q: 系统响应慢？

**可能原因**:
1. LLM API 响应慢
2. 知识库文档过多
3. 服务器资源不足

**解决方法**:
1. 更换更快的 LLM 服务商
2. 清理不必要的文档
3. 增加服务器内存/CPU
4. 使用流式模式提升感知速度

### Q: 内存占用过高？

**可能原因**:
1. 知识库文档过多
2. 并发用户过多
3. 内存泄漏

**解决方法**:
1. 限制知识库文档数量
2. 控制并发连接数
3. 定期重启服务
4. 使用 Docker 资源限制

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
```

### Q: 磁盘空间不足？

**清理建议**:
```bash
# 清理日志
rm -rf logs/*.log

# 清理旧的对话历史
rm -rf chat_history/old_*

# 清理向量数据库（谨慎操作）
# rm -rf rag/chroma_db/*

# Docker 清理
docker system prune -a
```

---

## 其他问题

### Q: 如何备份数据？

**备份脚本**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="./backups/$DATE"

mkdir -p $BACKUP_DIR

# 备份数据库
cp -r chat_history $BACKUP_DIR/
cp -r agent_memory $BACKUP_DIR/

# 备份知识库
cp -r rag/chroma_db $BACKUP_DIR/
cp -r rag/docs $BACKUP_DIR/

# 备份配置
cp .env $BACKUP_DIR/

echo "备份完成: $BACKUP_DIR"
```

### Q: 如何更新到最新版本？

```bash
# 1. 备份数据
./backup.sh

# 2. 拉取最新代码
git pull origin main

# 3. 更新依赖
./setup.sh install
cd frontend && npm install && cd ..

# 4. 重启服务
./start.sh
```

### Q: 如何重置所有数据？

**警告**: 此操作会删除所有数据，请谨慎使用！

```bash
# 停止服务
./stop.sh

# 删除数据目录
rm -rf chat_history/*
rm -rf agent_memory/*
rm -rf rag/chroma_db/*
rm -rf logs/*

# 重启服务
./start.sh
```

### Q: 如何查看日志？

```bash
# 实时查看日志
tail -f logs/agent-$(date +%Y-%m-%d).log

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend
```

---

## 获取帮助

如果以上方法无法解决你的问题：

1. **查看日志**: 后端日志通常包含详细错误信息
2. **搜索 Issues**: 在 GitHub Issues 中搜索类似问题
3. **提交 Issue**: 提供以下信息：
   - 操作系统和版本
   - Python/Node.js 版本
   - 完整的错误信息
   - 复现步骤
   - 相关日志片段

---

## 问题反馈

- GitHub Issues: https://github.com/your-username/langgraph-agent/issues
- 文档反馈: 请提交 PR 或 Issue

---

**最后更新**: 2024-01-15

## 下一步

- [对话模式说明](./chat-modes.md) - 了解 5 种对话模式
- [知识库使用指南](./knowledge-base.md) - 深入了解 RAG 功能
- [人工审核功能](./approval.md) - 了解审核机制
- [安装指南](../getting-started/installation.md) - 重新查看安装步骤
