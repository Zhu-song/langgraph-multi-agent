# 代码规范

本文档定义了 LangGraph 多智能体助手项目的代码规范。

## 通用规范

### 编码原则

1. **可读性优先**：代码是写给人看的，其次才是给机器执行的
2. **一致性**：保持与现有代码风格一致
3. **简洁性**：避免不必要的复杂度
4. **可维护性**：方便后续修改和扩展

---

## Python 规范

### 基础规范

遵循 [PEP 8](https://pep8.org/) 编码规范。

### 格式化工具

```bash
# 使用 Black 格式化
pip install black
black --line-length=100 .

# 使用 isort 排序导入
pip install isort
isort --profile black .

# 使用 Flake8 检查
pip install flake8
flake8 --max-line-length=100 .
```

### 导入顺序

```python
# 1. 标准库
import os
import json
from typing import Optional, List

# 2. 第三方库
from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

# 3. 本地模块
from config import settings
from tools import TOOLS
from utils.decorators import retry
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | 小写 + 下划线 | `calc_tool.py` |
| 类名 | 大驼峰 | `ChatRequest` |
| 函数名 | 小写 + 下划线 | `get_user_history` |
| 变量名 | 小写 + 下划线 | `user_id` |
| 常量 | 大写 + 下划线 | `MAX_RETRIES` |
| 私有方法 | 单下划线前缀 | `_compress_history` |

### 类型注解

所有函数必须添加类型注解：

```python
# ✅ 正确
def calculate(expression: str) -> str:
    """计算数学表达式"""
    pass

# ❌ 错误
def calculate(expression):
    pass
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def search_knowledge(query: str, top_k: int = 5) -> dict:
    """在知识库中搜索相关文档。

    使用向量相似度检索知识库中的相关文档片段。

    Args:
        query: 搜索查询文本。
        top_k: 返回最相关的文档数量，默认为 5。

    Returns:
        包含搜索结果的字典:
        {
            "results": [{"content": "...", "score": 0.95, "source": "doc.pdf"}],
            "total": 5
        }

    Raises:
        ValueError: 当 query 为空时。
        ConnectionError: 当数据库连接失败时。

    Examples:
        >>> search_knowledge("年假政策", top_k=3)
        {"results": [...], "total": 3}
    """
    pass
```

### 错误处理

```python
# ✅ 正确：具体异常 + 日志 + 友好提示
try:
    result = call_external_api(data)
except ConnectionError as e:
    logger.error(f"API 连接失败: {e}")
    return {"error": "服务暂时不可用，请稍后重试"}
except ValueError as e:
    logger.warning(f"参数错误: {e}")
    return {"error": f"参数无效: {e}"}
except Exception as e:
    logger.error(f"未知错误: {e}", exc_info=True)
    return {"error": "服务异常，请联系管理员"}

# ❌ 错误：裸 except
try:
    result = call_external_api(data)
except:
    return {"error": "错误"}
```

### 日志规范

```python
import logging

logger = logging.getLogger(__name__)

# 日志级别使用规范
logger.debug("调试信息 - 变量值: %s", variable)     # 开发调试
logger.info("常规信息 - 用户 %s 登录成功", user_id)   # 重要业务流程
logger.warning("警告 - API 响应超时，重试中...")       # 可恢复的问题
logger.error("错误 - 数据库写入失败: %s", error)       # 需要关注的错误
logger.critical("严重 - 服务无法启动")                  # 严重故障
```

---

## JavaScript/Vue 规范

### 基础规范

遵循 [Vue.js 官方风格指南](https://vuejs.org/style-guide/)。

### 格式化工具

```bash
# 使用 Prettier
npm install -D prettier
npx prettier --write "src/**/*.{js,vue,css}"

# 使用 ESLint
npm install -D eslint
npx eslint src/
```

### 组件命名

```javascript
// ✅ 正确：多词大驼峰
ChatPanel.vue
KnowledgeBase.vue
ApprovalRequest.vue

// ❌ 错误：单词或小写
chat.vue
knowledgebase.vue
```

### Props 定义

```javascript
// ✅ 正确：定义类型和默认值
const props = defineProps({
  userId: {
    type: String,
    required: true
  },
  mode: {
    type: String,
    default: 'smart_chat',
    validator: (value) => ['smart_chat', 'stream_chat', 'rag_chat'].includes(value)
  }
})
```

### 事件命名

```javascript
// ✅ 正确：kebab-case
this.$emit('update-conversation', data)
this.$emit('tool-approved', { toolName, result })

// ❌ 错误：camelCase
this.$emit('updateConversation', data)
```

### API 请求

```javascript
// 使用统一的 API 封装
import api from '@/api'

// ✅ 正确
async function sendMessage(userId, message) {
  try {
    const response = await api.post('/chat', {
      user_id: userId,
      message: message
    })
    return response.data
  } catch (error) {
    console.error('发送消息失败:', error)
    throw error
  }
}

// ❌ 错误：直接使用 axios
axios.post('/chat', data)
```

---

## Git 规范

### 分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能分支 | `feature/xxx` | `feature/weather-tool` |
| 修复分支 | `fix/xxx` | `fix/chat-history-loss` |
| 文档分支 | `docs/xxx` | `docs/api-documentation` |
| 重构分支 | `refactor/xxx` | `refactor/workflow-optimization` |

### .gitignore

确保以下内容在 `.gitignore` 中：

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
*.egg-info/

# Node.js
node_modules/
dist/

# 环境配置
.env
.env.local

# 数据
*.db
agent_memory/
chat_history/
rag/chroma_db/

# 日志
logs/

# IDE
.vscode/
.idea/
```

---

## 文件组织

### 后端目录结构

```
langgraph-agent/
├── main.py                 # FastAPI 入口
├── workflow.py             # LangGraph 工作流
├── config.py               # 配置管理
├── requirements.txt        # Python 依赖
├── tools/                  # 工具目录
│   ├── __init__.py
│   ├── calc_tool.py
│   ├── search_tool.py
│   └── ...
├── rag/                    # RAG 模块
│   ├── rag_core.py
│   └── lightrag.py
├── graphrag/               # 知识图谱模块
│   ├── builder.py
│   └── qa.py
├── utils/                  # 工具函数
│   ├── decorators.py
│   ├── retry.py
│   └── logger.py
└── tests/                  # 测试目录
    ├── test_tools.py
    └── test_workflow.py
```

### 前端目录结构

```
frontend/
├── src/
│   ├── main.js             # 入口文件
│   ├── App.vue             # 根组件
│   ├── api/                # API 封装
│   │   └── index.js
│   ├── components/         # 公共组件
│   │   ├── ChatPanel.vue
│   │   ├── KnowledgePanel.vue
│   │   └── ApprovalPanel.vue
│   ├── stores/             # Pinia 状态管理
│   │   ├── chat.js
│   │   ├── knowledge.js
│   │   └── approval.js
│   ├── assets/             # 静态资源
│   └── styles/             # 样式文件
├── public/                 # 公共资源
├── package.json
└── vite.config.js
```

---

## 注释规范

### Python 注释

```python
# ✅ 好的注释：解释 "为什么"
# 使用 MD5 校验避免重复索引相同文档
file_hash = hashlib.md5(content.encode()).hexdigest()

# ❌ 不好的注释：解释 "是什么"（代码本身已经说明）
# 获取文件名
file_name = os.path.basename(path)
```

### Vue 模板注释

```html
<!-- 工具调用状态指示器 -->
<div v-if="toolStatus === 'running'" class="tool-indicator">
  <span class="spinner"></span>
  <span>正在执行 {{ toolName }}...</span>
</div>
```

### TODO 注释

```python
# TODO(zhangsan): 2024-02-01 - 添加缓存机制提升查询速度
# FIXME: 并发场景下可能出现竞态条件
# HACK: 临时方案，等待上游 API 修复后移除
# NOTE: 这里使用 SQLite 是因为数据量较小，后续可迁移到 PostgreSQL
```

---

## 安全规范

### 输入验证

```python
# ✅ 始终验证用户输入
def get_user(user_id: str) -> dict:
    if not user_id or not user_id.isalnum():
        raise ValueError("无效的用户 ID")
    
    user = db.get_user(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    
    return user
```

### 敏感信息

```python
# ✅ 不在日志中打印敏感信息
logger.info(f"用户登录: user_id={user_id}")  # ✅
logger.info(f"用户登录: password={password}")  # ❌

# ✅ 不在代码中硬编码密钥
API_KEY = os.environ.get("API_KEY")  # ✅
API_KEY = "sk-xxxx"  # ❌
```

### SQL 注入防护

```python
# ✅ 使用参数化查询
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ❌ 字符串拼接
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
```

---

## 测试规范

### 测试命名

```python
# 格式：test_<功能>_<场景>_<预期结果>

def test_calculator_valid_expression_returns_result():
    """测试：有效表达式 → 返回计算结果"""
    pass

def test_calculator_division_by_zero_returns_error():
    """测试：除以零 → 返回错误"""
    pass

def test_search_empty_query_raises_value_error():
    """测试：空查询 → 抛出 ValueError"""
    pass
```

### 测试结构

```python
import pytest

class TestCalculatorTool:
    """计算器工具测试"""
    
    def setup_method(self):
        """每个测试前执行"""
        self.tool = calculator
    
    def test_addition(self):
        """测试加法运算"""
        result = self.tool("2 + 3")
        assert "5" in result
    
    def test_complex_expression(self):
        """测试复杂表达式"""
        result = self.tool("(1 + 2) * 3")
        assert "9" in result
    
    def test_invalid_expression(self):
        """测试无效表达式"""
        result = self.tool("abc")
        assert "错误" in result
```

---

## 检查清单

提交代码前，请确认：

- [ ] 代码通过 `flake8` 检查
- [ ] 代码通过 `black` 格式化
- [ ] 所有函数有类型注解
- [ ] 所有函数有文档字符串
- [ ] 新功能有对应测试
- [ ] 所有测试通过
- [ ] 无硬编码的密钥或密码
- [ ] 日志中无敏感信息
- [ ] Commit message 遵循规范
- [ ] 更新了相关文档

---

## 下一步

- [贡献指南](./contributing.md) - 了解如何参与项目
- [工具开发指南](../development/tools.md) - 学习工具开发
- [API 接口文档](../development/api.md) - 查看 API 文档
