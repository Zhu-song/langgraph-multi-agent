# 贡献指南

感谢你对 LangGraph 多智能体助手项目的关注！本文档将指导你如何参与项目贡献。

## 贡献方式

### 贡献类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 🐛 Bug 修复 | 修复已知问题 | 修复对话历史丢失问题 |
| ✨ 新功能 | 添加新功能 | 添加新的工具 |
| 📝 文档 | 改进文档 | 补充 API 文档 |
| 🎨 UI/UX | 改进界面 | 优化对话界面布局 |
| ⚡ 性能 | 性能优化 | 优化 RAG 检索速度 |
| 🔧 重构 | 代码重构 | 优化模块结构 |
| 🧪 测试 | 添加测试 | 添加工具单元测试 |

---

## 开始之前

### 1. Fork 项目

```bash
# 在 GitHub 上 Fork 项目
# 然后克隆你的 Fork
git clone https://github.com/your-username/langgraph-agent.git
cd langgraph-agent
```

### 2. 创建分支

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 或者修复分支
git checkout -b fix/bug-description
```

### 3. 设置开发环境

```bash
# 初始化虚拟环境
./setup.sh init

# 安装前端依赖
cd frontend && npm install && cd ..

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 4. 启动开发服务

```bash
./start.sh
```

---

## 开发流程

### 1. 编写代码

遵循 [代码规范](./code-style.md) 进行开发。

### 2. 测试

```bash
# 运行后端测试
cd venv && python -m pytest tests/ -v

# 运行前端测试
cd frontend && npm run test
```

### 3. 提交代码

```bash
# 查看修改
git status
git diff

# 暂存修改
git add .

# 提交（遵循提交规范）
git commit -m "feat(tools): 添加天气查询工具"
```

### 4. 推送并创建 PR

```bash
# 推送到你的 Fork
git push origin feature/your-feature-name

# 在 GitHub 上创建 Pull Request
```

---

## 提交规范

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>
```

### Type 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构（不新增功能也不修复 Bug） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具链相关 |

### Scope 范围

| Scope | 说明 |
|-------|------|
| `tools` | 工具相关 |
| `workflow` | 工作流相关 |
| `rag` | RAG 知识库相关 |
| `api` | API 接口相关 |
| `ui` | 前端界面相关 |
| `auth` | 认证相关 |
| `deploy` | 部署相关 |

### 示例

```
feat(tools): 添加天气查询工具

- 新增 weather_query 工具函数
- 支持查询当天和未来7天天气
- 添加单元测试

Closes #123
```

```
fix(workflow): 修复长对话压缩后丢失上下文的问题

压缩历史对话时保留了系统提示词，确保上下文连贯。
```

```
docs(api): 补充人工审核接口文档

添加审核状态检查和处理接口的详细说明。
```

---

## Pull Request 规范

### PR 标题

```
[类型] 简短描述
```

示例：
```
[feat] 添加天气查询工具
[fix] 修复对话历史丢失问题
[docs] 更新 API 文档
```

### PR 描述模板

```markdown
## 变更说明

简要描述本次变更的内容和目的。

## 变更类型

- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 其他

## 变更内容

### 后端
- 描述后端变更

### 前端
- 描述前端变更

### 文档
- 描述文档变更

## 测试

- [ ] 单元测试通过
- [ ] 手动测试通过
- [ ] 无回归问题

## 截图（如有）

添加相关截图。

## 关联 Issue

Closes #123
```

### PR 审查流程

1. **自动检查**：CI 自动运行测试和代码检查
2. **代码审查**：至少 1 位维护者审查通过
3. **合并**：维护者合并 PR

---

## Issue 规范

### Bug 报告

```markdown
## Bug 描述

清晰描述 Bug 的表现。

## 复现步骤

1. 步骤 1
2. 步骤 2
3. 步骤 3

## 期望行为

描述期望的正确行为。

## 实际行为

描述实际的错误行为。

## 环境信息

- OS: Ubuntu 22.04
- Python: 3.10
- Node.js: 18
- 浏览器: Chrome 120

## 错误日志

粘贴相关错误日志。
```

### 功能建议

```markdown
## 功能描述

描述你希望添加的功能。

## 动机

为什么需要这个功能？解决了什么问题？

## 建议实现

（可选）描述你建议的实现方式。

## 替代方案

（可选）是否有其他替代方案？
```

---

## 代码审查要点

审查者应关注以下方面：

### 功能正确性
- 代码是否实现了预期功能
- 边界条件是否处理正确
- 错误处理是否完善

### 代码质量
- 代码是否清晰易读
- 是否遵循代码规范
- 是否有重复代码

### 安全性
- 输入验证是否充分
- 是否有安全漏洞
- 敏感信息是否保护

### 性能
- 是否有性能瓶颈
- 数据库查询是否优化
- 是否有不必要的计算

### 测试
- 测试覆盖率是否足够
- 测试用例是否合理
- 是否有边界测试

---

## 发布流程

### 版本号规范

遵循语义化版本（Semantic Versioning）：

```
MAJOR.MINOR.PATCH
```

| 变更 | 版本号变化 | 示例 |
|------|-----------|------|
| 不兼容的 API 变更 | MAJOR +1 | 1.0.0 → 2.0.0 |
| 向后兼容的新功能 | MINOR +1 | 1.0.0 → 1.1.0 |
| 向后兼容的 Bug 修复 | PATCH +1 | 1.0.0 → 1.0.1 |

### 发布步骤

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git Tag
4. 构建并发布

---

## 社区准则

### 行为准则

- 尊重所有贡献者
- 接受建设性批评
- 关注代码本身而非个人
- 保持友好和专业的态度

### 沟通渠道

- **GitHub Issues**: Bug 报告和功能建议
- **Pull Requests**: 代码贡献
- **Discussions**: 问答和讨论

---

## 获取帮助

如果你在贡献过程中遇到问题：

1. 查阅 [文档中心](../README.md)
2. 搜索已有的 Issues
3. 在 GitHub Discussions 中提问
4. 提交 Issue 描述你的问题

---

感谢你的贡献！每一个 PR、Issue 和建议都让这个项目变得更好。
