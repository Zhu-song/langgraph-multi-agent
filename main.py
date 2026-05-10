# main.py
# FastAPI 接口化 + SSE 流式输出 + LightRAG + 增量更新 + 来源引用标注 + RAG真实流式输出 + 人工审核
from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from workflow import graph
from langchain_core.messages import HumanMessage
import json
import asyncio
from datetime import datetime
from typing import Any
import uuid
import sqlite3
import bcrypt
import threading
import logging

# 导入功能模块
from rag.lightrag import light_rag
from rag.rag_core import load_all_docs
from rag import rag_stream_generator

# 导入审核 API 路由
from api import approval_router

# 导入配置
from config import CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, APP_NAME, APP_VERSION, APP_DESCRIPTION

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ======================
# CORS 跨域配置（安全配置）
# ======================
# 解析允许的域名列表
allowed_origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# 注册审核 API 路由
app.include_router(approval_router)

# ======================
# 健康检查端点
# ======================
@app.get("/", 
    summary="根路径",
    description="返回 API 基本信息",
    tags=["系统"])
async def root():
    """根路径 - 返回 API 基本信息"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health",
    summary="健康检查",
    description="用于 Docker/K8s 健康检查，返回服务状态",
    tags=["系统"])
async def health_check():
    """健康检查端点 - 用于容器编排和负载均衡"""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ready",
    summary="就绪检查",
    description="检查服务是否准备好接收请求",
    tags=["系统"])
async def readiness_check():
    """就绪检查端点 - 检查依赖服务是否可用"""
    checks = {
        "api": True,
        "database": True
    }
    
    # 检查数据库连接（使用 try/finally 确保游标关闭）
    cursor = None
    try:
        cursor = chat_db.cursor()
        cursor.execute("SELECT 1")
    except Exception:
        checks["database"] = False
    finally:
        if cursor:
            cursor.close()
    
    all_healthy = all(checks.values())
    
    return {
        "ready": all_healthy,
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }

# ======================
# 请求体定义
# ======================
class ChatRequest(BaseModel):
    user_id: str
    query: str

class KnowledgeUpdateRequest(BaseModel):
    user_id: str
    is_incremental: bool = True

class ApprovalResumeRequest(BaseModel):
    user_id: str
    thread_id: str
    approved: bool

# ======================
# 辅助函数：安全执行 graph（处理 interrupt）
# ======================
async def run_graph_safely(user_id: str, query: str = None, resume_value: Any = None):
    """
    安全执行 graph，处理 interrupt（人工审核暂停）
    返回: {"reply": str, "needs_approval": bool, "tool_info": str}
    
    同一用户的所有对话共享上下文（thread_id = user_id）
    """
    # 兼容不同版本的 langgraph 导入
    try:
        from langgraph.types import Interrupt, Command
    except ImportError:
        import langgraph.types as lg_types
        Interrupt = lg_types.Interrupt
        Command = lg_types.Command
    GraphInterrupt = Interrupt

    config = {"configurable": {"thread_id": user_id}}
    loop = asyncio.get_event_loop()

    if resume_value is not None:
        def sync_invoke():
            return list(graph.stream(Command(resume=resume_value), config, stream_mode="values"))
    else:
        inputs = {"messages": [HumanMessage(content=query)]}
        def sync_invoke():
            return list(graph.stream(inputs, config, stream_mode="values"))

    reply = ""
    needs_approval = False
    tool_info = ""

    try:
        steps = await asyncio.to_thread(sync_invoke)

        for step in steps:
            messages = step.get("messages", [])
            if not messages:
                continue
            last = messages[-1]
            if hasattr(last, 'content') and last.content:
                reply = last.content
    except GraphInterrupt as e:
        needs_approval = True
        if hasattr(e, 'interrupts') and e.interrupts:
            for interrupt_obj in e.interrupts:
                val = getattr(interrupt_obj, 'value', None)
                if val:
                    tool_info = str(val)
                    break
        if not tool_info:
            tool_info = "工具调用等待审核"
        reply = ""

    # 再次通过 get_state 确认 interrupt 状态
    try:
        state = graph.get_state(config)
        if state.tasks:
            for task in state.tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    needs_approval = True
                    if not tool_info:
                        tool_info = str(task.interrupts[0].value) if task.interrupts else "未知工具"
                    break
    except (ConnectionError, TimeoutError) as e:
        logging.warning(f"获取工作流状态失败（网络问题）: {str(e)}")
    except Exception as e:
        logging.warning(f"获取工作流状态失败: {str(e)}")

    return {
        "reply": reply,
        "needs_approval": needs_approval,
        "tool_info": tool_info
    }

# ======================
# 1. 普通对话接口
# ======================
@app.post("/chat",
    summary="普通对话",
    description="发送消息给智能体，返回同步响应。支持人工审核中断。",
    tags=["对话"])
async def chat(req: ChatRequest):
    result = await run_graph_safely(req.user_id, req.query)
    
    return {
        "user_id": req.user_id,
        "reply": result["reply"],
        "needs_approval": result["needs_approval"],
        "tool_info": result["tool_info"]
    }

# ======================
# 2. SSE 流式对话接口（智能体工作流）
# ======================
async def stream_generator(req: ChatRequest):
    # 兼容不同版本的 langgraph 导入
    try:
        from langgraph.types import Interrupt
    except ImportError:
        import langgraph.types as lg_types
        Interrupt = lg_types.Interrupt
    GraphInterrupt = Interrupt

    config = {"configurable": {"thread_id": req.user_id}}
    inputs = {"messages": [HumanMessage(content=req.query)]}

    def sync_stream():
        return list(graph.stream(inputs, config, stream_mode="values"))

    last_content = ""
    needs_approval = False
    tool_info = ""
    step_count = 0

    try:
        steps = await asyncio.to_thread(sync_stream)

        for step in steps:
            step_count += 1
            messages = step.get("messages", [])
            if not messages:
                continue

            last = messages[-1]
            msg_type = last.type
            content = last.content if hasattr(last, 'content') else ""

            # 检测工具调用，推送状态提示
            if hasattr(last, "tool_calls") and last.tool_calls:
                tool_names = [tc.get("name", "") for tc in last.tool_calls]
                tools_str = ", ".join(tool_names)
                yield f"data: {json.dumps({'type': 'status', 'content': f'正在调用工具: {tools_str}...'})}\n\n"
                continue

            # 检测工具执行结果
            if msg_type == "tool":
                continue

            # AI 回复：增量推送
            if msg_type == "ai" and content and content != last_content:
                if step_count == 1:
                    yield f"data: {json.dumps({'type': 'status', 'content': '正在思考...'})}\n\n"
                new_content = content[len(last_content):]
                if new_content:
                    yield f"data: {json.dumps({'type': 'ai', 'content': new_content})}\n\n"
                last_content = content

    except GraphInterrupt as e:
        needs_approval = True
        if hasattr(e, 'interrupts') and e.interrupts:
            for interrupt_obj in e.interrupts:
                val = getattr(interrupt_obj, 'value', None)
                if val:
                    tool_info = str(val)
                    break
        if not tool_info:
            tool_info = "工具调用等待审核"

    # 再次通过 get_state 确认 interrupt 状态
    if not needs_approval:
        try:
            state = graph.get_state(config)
            if state.tasks:
                for task in state.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        needs_approval = True
                        tool_info = str(task.interrupts[0].value) if task.interrupts else "未知工具"
                        break
        except (ConnectionError, TimeoutError) as e:
            logging.warning(f"获取工作流状态失败（网络问题）: {str(e)}")
        except Exception as e:
            logging.warning(f"获取工作流状态失败: {str(e)}")

    yield f"data: {json.dumps({'type': 'done', 'needs_approval': needs_approval, 'tool_info': tool_info})}\n\n"

@app.post("/chat/stream",
    summary="SSE 流式对话",
    description="发送消息给智能体，通过 Server-Sent Events 实时返回响应流。",
    tags=["对话"])
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        stream_generator(req),
        media_type="text/event-stream"
    )

# ======================
# 3. LightRAG 混合检索接口
# ======================
@app.post("/rag",
    summary="LightRAG 混合检索",
    description="使用 LightRAG 进行混合检索（向量+图谱），返回同步响应。",
    tags=["知识库"])
async def rag_api(req: ChatRequest):
    answer = await asyncio.to_thread(light_rag.query, req.query, "hybrid")
    return {"user_id": req.user_id, "reply": answer}

# ======================
# 4. LightRAG 流式输出
# ======================
async def lightrag_stream_generator(req: ChatRequest):
    answer = await asyncio.to_thread(light_rag.query, req.query, "hybrid")
    for char in answer:
        yield f"data: {json.dumps({'type': 'ai', 'content': char})}\n\n"
        await asyncio.sleep(0.02)
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

@app.post("/rag/stream",
    summary="LightRAG 流式输出",
    description="使用 LightRAG 进行混合检索，通过 SSE 实时返回响应流。",
    tags=["知识库"])
async def rag_stream(req: ChatRequest):
    return StreamingResponse(lightrag_stream_generator(req), media_type="text/event-stream")

# ======================
# 5. 真实 RAG 流式输出
# ======================
async def real_rag_stream_gen(req: ChatRequest):
    async for token in rag_stream_generator(req.query):
        yield f"data: {json.dumps({'type': 'ai', 'content': token})}\n\n"
        await asyncio.sleep(0.01)
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

@app.post("/rag/real/stream",
    summary="真实 RAG 流式输出",
    description="使用真实 RAG 检索，通过 SSE 实时返回响应流。",
    tags=["知识库"])
async def rag_real_stream(req: ChatRequest):
    return StreamingResponse(real_rag_stream_gen(req), media_type="text/event-stream")

# ======================
# 6. 知识库增量/全量更新 API
# ======================
@app.post("/knowledge/update",
    summary="知识库更新",
    description="更新知识库，支持增量更新和全量重建。",
    tags=["知识库"])
async def update_knowledge(req: KnowledgeUpdateRequest):
    try:
        msg = await asyncio.to_thread(load_all_docs, req.is_incremental)
        return {"code": 200, "user_id": req.user_id, "success": True, "message": msg}
    except Exception as e:
        return {"code": 500, "user_id": req.user_id, "success": False, "message": f"更新失败：{str(e)}"}

# ======================
# 7. 知识库状态 API
# ======================
@app.get("/api/knowledge/status",
    summary="知识库状态",
    description="获取知识库当前状态，包括文档数量、数据库类型等信息。",
    tags=["知识库"])
def get_knowledge_status():
    import os
    doc_dir = "./rag/docs"
    doc_count = 0
    if os.path.exists(doc_dir):
        doc_count = len([f for f in os.listdir(doc_dir) if f.endswith(('.txt', '.md', '.pdf'))])
    return {
        "code": 200, "message": "success",
        "data": {"doc_count": doc_count, "vector_db": "ChromaDB", "graph_db": "Neo4j",
                 "last_update": datetime.now().isoformat() if doc_count > 0 else None}
    }

# ======================
# 8. 知识图谱构建 API
# ======================
@app.post("/api/knowledge/graph/build",
    summary="构建知识图谱",
    description="从文档构建 Neo4j 知识图谱，包括实体抽取和关系建立。",
    tags=["知识库"])
async def build_knowledge_graph():
    try:
        from graphrag import build_graph_from_docs
        result = await asyncio.to_thread(build_graph_from_docs)
        return {"code": 200, "message": result, "data": None}
    except Exception as e:
        return {"code": 500, "message": f"构建失败：{str(e)}", "data": None}

# ======================
# 9. 用户管理 API（含密码认证）
# ======================

# 对话历史数据库
CHAT_DB_PATH = "chat_history.db"

# 使用线程本地存储管理数据库连接
_db_local = threading.local()

def get_db_connection():
    """获取当前线程的数据库连接（线程安全）"""
    if not hasattr(_db_local, 'connection') or _db_local.connection is None:
        _db_local.connection = sqlite3.connect(CHAT_DB_PATH, check_same_thread=False)
        # 启用 WAL 模式提高并发性能
        _db_local.connection.execute("PRAGMA journal_mode=WAL")
        _db_local.connection.execute("PRAGMA busy_timeout=5000")
    return _db_local.connection

def get_db_cursor():
    """获取数据库游标"""
    return get_db_connection().cursor()

def hash_password(password: str) -> str:
    """密码哈希（bcrypt）- 安全的密码存储方式"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def init_chat_db():
    """初始化对话历史数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT DEFAULT '新用户',
            password TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT DEFAULT '新对话',
            pinned INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conv_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (conv_id) REFERENCES conversations(id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conv_id)')
    
    # 兼容旧数据库：添加缺失的列
    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN pinned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    
    # 确保所有现有用户的 password 字段不为 NULL
    try:
        cursor.execute("UPDATE users SET password = '' WHERE password IS NULL")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    return conn

# 为了向后兼容，创建一个代理类
class DatabaseProxy:
    """数据库连接代理，自动使用线程安全的连接"""
    def cursor(self):
        return get_db_cursor()
    
    def commit(self):
        get_db_connection().commit()
    
    def execute(self, *args, **kwargs):
        return get_db_connection().execute(*args, **kwargs)

chat_db = DatabaseProxy()

# 初始化数据库表
init_chat_db()

@app.post("/api/auth/register",
    summary="用户注册",
    description="注册新用户，需要提供用户名和密码（至少6位）。",
    tags=["用户认证"])
def register(name: str = Body(..., embed=True), password: str = Body(..., embed=True)):
    """用户注册（用户名+密码）"""
    if len(password) < 6:
        return {"code": 400, "message": "密码至少6位"}
    
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    pwd_hash = hash_password(password)
    
    cursor = chat_db.cursor()
    # 检查用户名是否已存在
    cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
    if cursor.fetchone():
        return {"code": 409, "message": "用户名已存在"}
    
    cursor.execute(
        "INSERT INTO users (id, name, password, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, pwd_hash, now, now)
    )
    chat_db.commit()
    return {"code": 200, "data": {"id": user_id, "name": name, "created_at": now}}

@app.post("/api/auth/login",
    summary="用户登录",
    description="使用用户名和密码登录，返回用户信息。",
    tags=["用户认证"])
def auth_login(name: str = Body(..., embed=True), password: str = Body(..., embed=True)):
    """用户登录（验证密码）"""
    cursor = chat_db.cursor()
    cursor.execute(
        "SELECT id, name, password FROM users WHERE name = ?",
        (name,)
    )
    row = cursor.fetchone()
    
    if not row:
        return {"code": 404, "message": "用户不存在"}
    
    # 使用 bcrypt 验证密码
    if not verify_password(password, row[2]):
        return {"code": 401, "message": "密码错误"}
    
    # 更新登录时间
    now = datetime.now().isoformat()
    cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, row[0]))
    chat_db.commit()
    
    return {"code": 200, "data": {"id": row[0], "name": row[1], "last_login": now}}

@app.post("/api/auth/verify",
    summary="验证用户密码",
    description="验证用户密码，用于切换用户时的身份验证。",
    tags=["用户认证"])
def auth_verify(user_id: str = Body(..., embed=True), password: str = Body(..., embed=True)):
    """验证用户密码（切换用户时使用）"""
    cursor = chat_db.cursor()
    cursor.execute("SELECT id, name, password FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        return {"code": 404, "message": "用户不存在"}
    
    # 使用 bcrypt 验证密码
    if not verify_password(password, row[2]):
        return {"code": 401, "message": "密码错误"}
    
    now = datetime.now().isoformat()
    cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))
    chat_db.commit()
    
    return {"code": 200, "data": {"id": row[0], "name": row[1]}}

@app.post("/api/auth/reset-password",
    summary="重置密码",
    description="重置用户密码（忘记密码功能），需要提供用户名和新密码。注意：此接口需要额外的安全验证。",
    tags=["用户认证"])
def reset_password(name: str = Body(..., embed=True), new_password: str = Body(..., embed=True)):
    """重置密码（忘记密码功能，验证用户名后直接重置）"""
    if len(new_password) < 6:
        return {"code": 400, "message": "新密码至少6位"}
    
    cursor = chat_db.cursor()
    cursor.execute("SELECT id, name FROM users WHERE name = ?", (name,))
    row = cursor.fetchone()
    
    if not row:
        return {"code": 404, "message": "用户不存在"}
    
    pwd_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (pwd_hash, row[0]))
    chat_db.commit()
    
    return {"code": 200, "message": "密码已重置", "data": {"id": row[0], "name": row[1]}}

@app.get("/api/users",
    summary="获取用户列表",
    description="获取所有用户列表，不包含密码信息。",
    tags=["用户管理"])
def get_users():
    """获取所有用户列表（不含密码）"""
    cursor = chat_db.cursor()
    cursor.execute(
        "SELECT id, name, created_at, last_login FROM users ORDER BY last_login DESC"
    )
    rows = cursor.fetchall()
    users = [
        {"id": row[0], "name": row[1], "created_at": row[2], "last_login": row[3]}
        for row in rows
    ]
    return {"code": 200, "data": {"users": users}}

@app.put("/api/users/{user_id}",
    summary="修改用户名",
    description="修改指定用户的用户名。",
    tags=["用户管理"])
def update_user(user_id: str, name: str = Body(..., embed=True)):
    """修改用户名"""
    cursor = chat_db.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    chat_db.commit()
    return {"code": 200, "message": "用户名已更新"}

@app.put("/api/users/{user_id}/password",
    summary="修改密码",
    description="修改用户密码，需要验证原密码。",
    tags=["用户管理"])
def change_password(user_id: str, old_password: str = Body(..., embed=True), new_password: str = Body(..., embed=True)):
    """修改密码"""
    if len(new_password) < 6:
        return {"code": 400, "message": "新密码至少6位"}
    
    cursor = chat_db.cursor()
    cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or not verify_password(old_password, row[0]):
        return {"code": 401, "message": "原密码错误"}
    
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_password), user_id))
    chat_db.commit()
    return {"code": 200, "message": "密码已修改"}

@app.delete("/api/users/{user_id}",
    summary="删除用户",
    description="删除指定用户及其所有对话历史。",
    tags=["用户管理"])
def delete_user(user_id: str):
    """删除用户及其所有对话（使用事务保护）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 开始事务
        conn.execute("BEGIN")
        cursor.execute("""
            DELETE FROM messages WHERE conv_id IN (
                SELECT id FROM conversations WHERE user_id = ?
            )
        """, (user_id,))
        cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return {"code": 200, "message": "用户已删除"}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "message": f"删除失败：{str(e)}"}

# ======================
# 10. 会话管理 API（SQLite 持久化）
# ======================

@app.get("/api/history/{user_id}",
    summary="获取对话历史",
    description="获取用户的所有对话列表，置顶对话排在前面。",
    tags=["会话管理"])
def get_conversation_history(user_id: str):
    cursor = chat_db.cursor()
    # 置顶的排在前面，然后按更新时间倒序
    cursor.execute(
        "SELECT id, title, pinned, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY pinned DESC, updated_at DESC, created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conversations = [
        {"id": row[0], "title": row[1], "pinned": bool(row[2]), "created_at": row[3], "updated_at": row[4]}
        for row in rows
    ]
    return {"code": 200, "message": "success", "data": {"conversations": conversations}}

@app.post("/api/conversation/new/{user_id}",
    summary="创建新对话",
    description="为指定用户创建一个新的对话。",
    tags=["会话管理"])
def create_new_conversation(user_id: str):
    conv_id = f"conv_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    cursor = chat_db.cursor()
    cursor.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (conv_id, user_id, "新对话", now, now)
    )
    chat_db.commit()
    return {"code": 200, "message": "success", "data": {"id": conv_id, "title": "新对话", "created_at": now}}

@app.get("/api/conversation/{user_id}/{conv_id}",
    summary="获取对话详情",
    description="获取指定对话的详细信息，包括所有消息。",
    tags=["会话管理"])
def get_conversation(user_id: str, conv_id: str):
    cursor = chat_db.cursor()
    cursor.execute(
        "SELECT id, title, created_at FROM conversations WHERE id = ? AND user_id = ?",
        (conv_id, user_id)
    )
    conv = cursor.fetchone()
    if not conv:
        return {"code": 404, "message": "对话不存在", "data": None}
    
    cursor.execute(
        "SELECT role, content, timestamp FROM messages WHERE conv_id = ? ORDER BY id ASC",
        (conv_id,)
    )
    rows = cursor.fetchall()
    messages = [
        {"role": row[0], "content": row[1], "timestamp": row[2]}
        for row in rows
    ]
    return {"code": 200, "message": "success", "data": {"id": conv_id, "title": conv[1], "created_at": conv[2], "messages": messages}}

@app.post("/api/conversation/{user_id}/{conv_id}/message",
    summary="添加消息",
    description="向指定对话添加一条消息。",
    tags=["会话管理"])
def add_conversation_message(user_id: str, conv_id: str, role: str = Body(...), content: str = Body(...)):
    """添加消息到对话（前端调用）"""
    cursor = chat_db.cursor()
    # 验证对话存在
    cursor.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
    if not cursor.fetchone():
        return {"code": 404, "message": "对话不存在", "data": None}
    
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO messages (conv_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (conv_id, role, content, now)
    )
    # 更新对话的 updated_at
    cursor.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id))
    chat_db.commit()
    return {"code": 200, "message": "success", "data": {"timestamp": now}}

@app.put("/api/conversation/{user_id}/{conv_id}/title",
    summary="更新对话标题",
    description="修改指定对话的标题。",
    tags=["会话管理"])
def update_conversation_title(user_id: str, conv_id: str, title: str = Body(..., embed=True)):
    """更新对话标题"""
    cursor = chat_db.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (title, datetime.now().isoformat(), conv_id, user_id)
    )
    chat_db.commit()
    return {"code": 200, "message": "标题已更新", "data": None}

@app.put("/api/conversation/{user_id}/{conv_id}/pinned",
    summary="设置置顶状态",
    description="设置或取消对话的置顶状态。",
    tags=["会话管理"])
def toggle_conversation_pinned(user_id: str, conv_id: str, pinned: bool = Body(..., embed=True)):
    """设置/取消置顶"""
    cursor = chat_db.cursor()
    cursor.execute(
        "UPDATE conversations SET pinned = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (1 if pinned else 0, datetime.now().isoformat(), conv_id, user_id)
    )
    chat_db.commit()
    return {"code": 200, "message": "置顶状态已更新", "data": {"pinned": pinned}}

@app.delete("/api/conversation/{user_id}/{conv_id}",
    summary="删除对话",
    description="删除指定的对话及其所有消息。",
    tags=["会话管理"])
def delete_conversation(user_id: str, conv_id: str):
    """删除单个对话（使用事务保护）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN")
        cursor.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
        conn.commit()
        return {"code": 200, "message": "对话已删除", "data": None}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "message": f"删除失败：{str(e)}"}

@app.delete("/api/history/{user_id}",
    summary="清空对话历史",
    description="清除用户的所有对话历史。",
    tags=["会话管理"])
def clear_conversation_history(user_id: str):
    """清除用户所有对话历史（使用事务保护）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN")
        # 先获取所有对话ID
        cursor.execute("SELECT id FROM conversations WHERE user_id = ?", (user_id,))
        conv_ids = [row[0] for row in cursor.fetchall()]
        # 删除消息
        for conv_id in conv_ids:
            cursor.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
        # 删除对话
        cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        conn.commit()
        return {"code": 200, "message": "对话历史已清空", "data": None}
    except Exception as e:
        conn.rollback()
        return {"code": 500, "message": f"清空失败：{str(e)}"}

# ======================
# 11. 工作流审核：检查 + 恢复
# ======================
@app.get("/api/approval/check/{user_id}",
    summary="检查审核状态",
    description="检查当前会话是否处于等待人工审核状态。",
    tags=["人工审核"])
def check_approval_status(user_id: str):
    """检查当前会话是否处于 interrupt（等待人工审核）状态"""
    config = {"configurable": {"thread_id": user_id}}
    state = graph.get_state(config)
    
    needs_approval = False
    tool_info = ""
    
    if state.tasks:
        for task in state.tasks:
            if hasattr(task, 'interrupts') and task.interrupts:
                needs_approval = True
                tool_info = str(task.interrupts[0].value) if task.interrupts else "未知工具"
                break
    
    return {
        "code": 200,
        "data": {"needs_approval": needs_approval, "tool_info": tool_info, "thread_id": user_id}
    }

@app.post("/api/approval/resume",
    summary="恢复工作流",
    description="审核通过或拒绝后恢复工作流执行。",
    tags=["人工审核"])
async def resume_after_approval(req: ApprovalResumeRequest):
    """审核通过/拒绝后恢复工作流执行"""
    # 先获取 interrupt 信息用于写入历史
    config = {"configurable": {"thread_id": req.thread_id}}
    tool_info = "未知工具"
    try:
        state = graph.get_state(config)
        if state.tasks:
            for task in state.tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    tool_info = str(task.interrupts[0].value) if task.interrupts else "未知工具"
                    break
    except (ConnectionError, TimeoutError) as e:
        logging.warning(f"获取工作流状态失败（网络问题）: {str(e)}")
    except Exception as e:
        logging.warning(f"获取工作流状态失败: {str(e)}")

    # 写入审核历史（旧审核系统兼容）
    from api.approval_api import APPROVAL_HISTORY, ApprovalInfo
    history_record = ApprovalInfo(
        id=f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        tool_name=tool_info,
        tool_args={},
        user_id=req.user_id,
        status="approved" if req.approved else "rejected",
        created_at=datetime.now().isoformat(),
        resolved_at=datetime.now().isoformat()
    )
    if req.user_id not in APPROVAL_HISTORY:
        APPROVAL_HISTORY[req.user_id] = []
    APPROVAL_HISTORY[req.user_id].append(history_record)

    # 恢复工作流
    result = await run_graph_safely(
        req.thread_id,
        resume_value="yes" if req.approved else "no"
    )

    return {
        "code": 200,
        "message": "审核已处理",
        "data": {
            "approved": req.approved,
            "reply": result["reply"],
            "needs_approval": result["needs_approval"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
