# 工具开发指南

本文档介绍如何为 LangGraph 多智能体助手开发自定义工具。

## 工具概述

### 什么是工具

工具是 Agent 可以调用的功能模块，让 LLM 能够：
- 获取外部信息（搜索、查询数据库）
- 执行计算（数学运算、数据处理）
- 操作文件（读写、删除）
- 访问私有知识（RAG、知识图谱）
- 执行计划（Plan-Execute 任务分解）

### 工具架构

```
用户提问
    ↓
LLM 判断需要调用工具
    ↓
生成 tool_call（工具名称 + 参数）
    ↓
ToolNode 执行对应工具函数
    ↓
返回 ToolMessage 给 LLM
    ↓
LLM 生成最终回答
```

## 快速开始

### 1. 创建工具文件

在 `tools/` 目录下创建新文件：

```bash
touch tools/my_tool.py
```

### 2. 编写工具函数

```python
# tools/my_tool.py

def my_tool_function(param1: str, param2: int = 10) -> str:
    """
    工具功能描述，LLM 会根据这个描述决定何时调用此工具。
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述，默认为10
        
    Returns:
        返回结果的描述
    """
    # 工具逻辑
    result = f"处理 {param1}，参数2为 {param2}"
    return result
```

### 3. 注册工具

在 `tools/__init__.py` 中注册：

```python
from .my_tool import my_tool_function

# 添加到工具列表
TOOLS = [
    # ... 其他工具
    my_tool_function,
]
```

### 4. 重启服务

```bash
./start.sh
```

## 工具开发规范

### 函数签名

```python
def tool_name(
    required_param: str,           # 必填参数
    optional_param: int = 10,      # 可选参数（有默认值）
    flag_param: bool = False       # 布尔标志参数
) -> str:
    """
    工具的简短描述（一句话）。
    
    工具的详细描述，说明：
    - 工具的功能
    - 使用场景
    - 返回值格式
    - 注意事项
    
    Args:
        required_param: 必填参数的描述
        optional_param: 可选参数的描述，默认值为10
        flag_param: 布尔参数的描述
        
    Returns:
        返回结果的详细描述
        
    Examples:
        >>> tool_name("test", 20)
        '处理 test，参数2为 20'
    """
    pass
```

### 参数类型

支持的参数类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `str` | 字符串 | `"hello"` |
| `int` | 整数 | `42` |
| `float` | 浮点数 | `3.14` |
| `bool` | 布尔值 | `True` |
| `list` | 列表 | `["a", "b"]` |
| `dict` | 字典 | `{"key": "value"}` |
| `Optional[T]` | 可选类型 | `Optional[str]` |

### 返回值

建议返回类型：

```python
# 简单结果 - 返回字符串
def simple_tool() -> str:
    return "操作成功"

# 结构化结果 - 返回 JSON 字符串
def structured_tool() -> str:
    import json
    result = {
        "status": "success",
        "data": {...},
        "message": "操作完成"
    }
    return json.dumps(result, ensure_ascii=False)

# 错误处理 - 返回错误信息
def tool_with_error() -> str:
    try:
        # 操作
        return "成功"
    except Exception as e:
        return f"错误: {str(e)}"
```

## 完整示例

### 示例 1：天气查询工具

```python
# tools/weather_tool.py

import requests
from typing import Optional

def weather_query(
    city: str,
    days: int = 1
) -> str:
    """
    查询指定城市的天气信息。
    
    支持查询当天或未来几天的天气预报，包括温度、湿度、天气状况等。
    
    Args:
        city: 城市名称，如"北京"、"上海"
        days: 查询天数，1-7天，默认为1（当天）
        
    Returns:
        天气信息的格式化字符串
        
    Examples:
        >>> weather_query("北京")
        '北京今天天气：晴，温度 25°C，湿度 45%'
        
        >>> weather_query("上海", 3)
        '上海未来3天天气：...'
    """
    try:
        # 这里调用真实的天气 API
        # 示例使用模拟数据
        weather_data = {
            "city": city,
            "days": days,
            "current": {
                "temperature": 25,
                "humidity": 45,
                "condition": "晴"
            }
        }
        
        if days == 1:
            return f"{city}今天天气：{weather_data['current']['condition']}，" \
                   f"温度 {weather_data['current']['temperature']}°C，" \
                   f"湿度 {weather_data['current']['humidity']}%"
        else:
            return f"{city}未来{days}天天气预报：..."
            
    except Exception as e:
        return f"查询天气失败: {str(e)}"
```

### 示例 2：数据库查询工具

```python
# tools/db_tool.py

import sqlite3
from typing import Optional

def db_query(
    query: str,
    params: Optional[list] = None
) -> str:
    """
    执行 SQLite 数据库查询。
    
    用于查询本地数据库中的数据，支持 SELECT 语句。
    注意：此工具仅支持查询，不支持修改数据。
    
    Args:
        query: SQL 查询语句，必须是 SELECT 开头
        params: 查询参数列表，用于参数化查询
        
    Returns:
        查询结果的 JSON 字符串
        
    Examples:
        >>> db_query("SELECT * FROM users WHERE age > ?", [18])
        '{"status": "success", "count": 5, "data": [...]}'
    """
    import json
    
    # 安全检查：只允许 SELECT 语句
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({
            "status": "error",
            "message": "仅支持 SELECT 查询"
        }, ensure_ascii=False)
    
    try:
        conn = sqlite3.connect("data.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        
        return json.dumps({
            "status": "success",
            "count": len(result),
            "data": result
        }, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)
    finally:
        conn.close()
```

### 示例 3：文件处理工具

```python
# tools/file_processor.py

import os
from typing import Optional

def file_processor(
    file_path: str,
    operation: str = "read",
    content: Optional[str] = None
) -> str:
    """
    文件处理工具，支持读取、写入、追加操作。
    
    注意：写入和删除操作属于高危操作，会触发人工审核。
    
    Args:
        file_path: 文件路径（相对路径，基于 data/ 目录）
        operation: 操作类型，可选 "read"/"write"/"append"/"delete"
        content: 写入内容（write/append 操作时需要）
        
    Returns:
        操作结果或文件内容
        
    Examples:
        >>> file_processor("test.txt", "read")
        '文件内容...'
        
        >>> file_processor("test.txt", "write", "Hello World")
        '文件写入成功'
    """
    # 安全检查：限制文件路径
    base_dir = "./data"
    full_path = os.path.join(base_dir, file_path)
    
    # 防止目录遍历攻击
    if not full_path.startswith(os.path.abspath(base_dir)):
        return "错误: 非法文件路径"
    
    try:
        if operation == "read":
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        elif operation == "write":
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content or "")
            return f"文件写入成功: {file_path}"
            
        elif operation == "append":
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content or "")
            return f"内容追加成功: {file_path}"
            
        elif operation == "delete":
            os.remove(full_path)
            return f"文件删除成功: {file_path}"
            
        else:
            return f"错误: 不支持的操作 {operation}"
            
    except FileNotFoundError:
        return f"错误: 文件不存在 {file_path}"
    except Exception as e:
        return f"错误: {str(e)}"
```

## 高级特性

### 1. 工具装饰器

使用装饰器添加额外功能：

```python
from utils.decorators import retry, trace_log

@retry(max_attempts=3)
@trace_log
def my_tool(param: str) -> str:
    """带重试和日志记录的工具"""
    return "result"
```

### 2. 异步工具

支持异步执行的工具：

```python
import asyncio

async def async_tool(param: str) -> str:
    """异步工具"""
    await asyncio.sleep(1)
    return f"异步结果: {param}"
```

### 3. 工具组合

工具可以调用其他工具：

```python
def complex_tool(query: str) -> str:
    """组合多个工具"""
    # 先搜索
    search_result = search_tool.web_search(query)
    
    # 再总结
    summary = summary_tool.summary(search_result)
    
    return summary
```

## 工具测试

### 单元测试

```python
# tests/test_my_tool.py

import pytest
from tools.my_tool import my_tool_function

def test_my_tool():
    result = my_tool_function("test", 20)
    assert "test" in result
    assert "20" in result

def test_my_tool_error():
    result = my_tool_function("")
    assert "错误" in result
```

### 集成测试

```python
# 测试工具在 Agent 中的使用
from workflow import graph

def test_tool_in_agent():
    config = {"configurable": {"thread_id": "test"}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "使用 my_tool 处理 test"}]},
        config
    )
    assert result is not None
```

## 最佳实践

### 1. 文档字符串

- 必须包含功能描述
- 详细说明参数
- 提供使用示例
- 说明返回值格式

### 2. 错误处理

```python
def robust_tool(param: str) -> str:
    try:
        # 主逻辑
        result = do_something(param)
        return result
    except ValueError as e:
        return f"参数错误: {str(e)}"
    except ConnectionError as e:
        return f"连接失败: {str(e)}"
    except Exception as e:
        return f"未知错误: {str(e)}"
```

### 3. 安全检查

```python
def secure_tool(user_input: str) -> str:
    # 输入验证
    if not user_input or len(user_input) > 1000:
        return "错误: 输入无效"
    
    # 防止注入攻击
    dangerous_chars = [';', '--', '/*', '*/']
    for char in dangerous_chars:
        if char in user_input:
            return "错误: 输入包含非法字符"
    
    # 执行操作
    return process(user_input)
```

### 4. 性能优化

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_tool(param: str) -> str:
    """带缓存的工具"""
    # 耗时操作
    return expensive_operation(param)
```

## 工具注册表

### 自动注册

```python
# tools/__init__.py

import os
import importlib
from typing import List, Callable

# 自动发现并注册所有工具
TOOLS: List[Callable] = []

def auto_register_tools():
    """自动注册 tools 目录下的所有工具函数"""
    current_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(current_dir):
        if filename.endswith('_tool.py'):
            module_name = filename[:-3]
            module = importlib.import_module(f'.{module_name}', package='tools')
            
            # 查找模块中的工具函数
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '__doc__'):
                    TOOLS.append(attr)

auto_register_tools()
```

### 手动注册

```python
# tools/__init__.py

from .calc_tool import calculator
from .search_tool import web_search
from .translate_tool import translate
from .my_tool import my_tool_function
from .plan_execute_tool import plan_execute

TOOLS = [
    calculator,
    web_search,
    translate,
    my_tool_function,  # 添加新工具
    plan_execute,
]
```

## 调试技巧

### 1. 日志输出

```python
import logging

logger = logging.getLogger(__name__)

def debug_tool(param: str) -> str:
    logger.debug(f"工具被调用，参数: {param}")
    
    result = do_something(param)
    
    logger.debug(f"工具执行结果: {result}")
    return result
```

### 2. 本地测试

```python
# 直接运行测试
if __name__ == "__main__":
    # 测试工具
    result = my_tool_function("test", 20)
    print(result)
    
    # 测试错误情况
    result = my_tool_function("")
    print(result)
```

## 内置工具列表

项目内置了 16 个工具，按功能分类如下：

### 通用工具

| 工具 | 文件 | 说明 |
|------|------|------|
| `calculator` | `calc_tool.py` | 安全数学表达式解析（递归下降，非 eval） |
| `web_search` | `search_tool.py` | 百度搜索 + LLM 精炼总结（高危，需审核） |
| `translate` | `translate_tool.py` | 中英文互译 |
| `summary` | `summary_tool.py` | 长文本摘要总结 |
| `json_tool` | `json_tool.py` | JSON 格式化/校验 |
| `time_tool` | `time_tool.py` | 时间日期查询 |
| `random_tool` | `random_tool.py` | 随机数/密码/抽签 |

### 文本工具

| 工具 | 文件 | 说明 |
|------|------|------|
| `text_stat` | `text_stat_tool.py` | 字数统计/清洗 |
| `text_format` | `text_format_tool.py` | 大小写/驼峰/下划线转换 |

### 文件工具

| 工具 | 文件 | 说明 |
|------|------|------|
| `file_tool` | `file_tool.py` | 文件创建/读取/写入 |
| `file_delete` | `file_tool.py` | 文件删除（高危，需审核） |

### 知识库工具

| 工具 | 文件 | 说明 |
|------|------|------|
| `rag_knowledge_query` | `rag_tools.py` | 私有文档 RAG 问答 |
| `graph_knowledge_query` | `graphrag_tool.py` | 知识图谱实体关系问答 |
| `lightrag_operate` | `lightrag_tool.py` | LightRAG 双层检索（local/global/hybrid） |
| `incremental_rag_operate` | `rag_tools.py` | 知识库增量/全量更新 |

### 元认知工具

| 工具 | 文件 | 说明 |
|------|------|------|
| `reflection_self_check` | `reflection_tool.py` | 答案自省纠错/润色 |

### 计划执行工具

| 工具 | 文件 | 说明 |
|------|------|------|
| `plan_execute` | `plan_execute_tool.py` | 复杂任务分解与执行（Plan-Execute 模式） |

## 下一步

- [API 接口文档](./api.md) - 了解后端 API 设计
- [工作流详解](./workflow.md) - 深入了解 LangGraph 工作流
- [代码规范](../contributing/code-style.md) - 遵循代码规范
