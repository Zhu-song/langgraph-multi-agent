# api/approval_api.py
# 人工审核 API 模块
# 功能：管理高危工具调用的人工审核流程

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
import uuid
from config import HIGH_RISK_TOOLS

# 创建路由器
router = APIRouter(prefix="/api/approval", tags=["人工审核"])

# ==================== 数据模型 ====================

class ApprovalRequest(BaseModel):
    """审核请求"""
    tool_name: str
    tool_args: Dict
    user_id: str
    conversation_id: Optional[str] = None

class ApprovalSubmit(BaseModel):
    """提交审核结果"""
    user_id: str
    approval_id: str
    approved: bool
    reason: Optional[str] = ""

class ApprovalInfo(BaseModel):
    """审核信息"""
    id: str
    tool_name: str
    tool_args: Dict
    user_id: str
    status: str  # pending, approved, rejected, timeout
    created_at: str
    resolved_at: Optional[str] = None
    reason: Optional[str] = None

# ==================== 内存存储（生产环境应使用 Redis/数据库） ====================

# 待审核请求存储
PENDING_APPROVALS: Dict[str, ApprovalInfo] = {}

# 审核历史记录
APPROVAL_HISTORY: Dict[str, List[ApprovalInfo]] = {}

# 审核超时时间（秒）
APPROVAL_TIMEOUT = 30

# ==================== API 接口 ====================

@router.post("/request")
async def create_approval_request(req: ApprovalRequest):
    """
    创建审核请求
    当智能体需要调用高危工具时，前端调用此接口创建审核请求
    """
    # 检查是否为高危工具
    if req.tool_name not in HIGH_RISK_TOOLS:
        return {
            "code": 200,
            "message": "低风险工具，无需审核",
            "data": {"need_approval": False}
        }
    
    # 生成审核ID
    approval_id = f"approval_{uuid.uuid4().hex[:12]}"
    
    # 创建审核信息
    approval_info = ApprovalInfo(
        id=approval_id,
        tool_name=req.tool_name,
        tool_args=req.tool_args,
        user_id=req.user_id,
        status="pending",
        created_at=datetime.now().isoformat()
    )
    
    # 存储待审核请求
    PENDING_APPROVALS[approval_id] = approval_info
    
    return {
        "code": 200,
        "message": "审核请求已创建",
        "data": {
            "need_approval": True,
            "approval_id": approval_id,
            "tool_name": req.tool_name,
            "timeout": APPROVAL_TIMEOUT
        }
    }

@router.get("/pending/{user_id}")
async def get_pending_approvals(user_id: str):
    """
    获取用户的待审核请求列表
    前端轮询此接口获取待审核请求
    """
    pending = [
        info.model_dump() for info in PENDING_APPROVALS.values()
        if info.user_id == user_id and info.status == "pending"
    ]
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "pending_count": len(pending),
            "approvals": pending
        }
    }

@router.post("/submit")
async def submit_approval(req: ApprovalSubmit):
    """
    提交审核结果
    用户批准或拒绝工具调用
    """
    if req.approval_id not in PENDING_APPROVALS:
        return {
            "code": 404,
            "message": "审核请求不存在或已过期",
            "data": None
        }
    
    approval_info = PENDING_APPROVALS[req.approval_id]
    
    # 检查是否为该用户的审核请求
    if approval_info.user_id != req.user_id:
        return {
            "code": 403,
            "message": "无权操作此审核请求",
            "data": None
        }
    
    # 更新审核状态
    approval_info.status = "approved" if req.approved else "rejected"
    approval_info.resolved_at = datetime.now().isoformat()
    approval_info.reason = req.reason
    
    # 移动到历史记录
    if req.user_id not in APPROVAL_HISTORY:
        APPROVAL_HISTORY[req.user_id] = []
    APPROVAL_HISTORY[req.user_id].append(approval_info)
    
    # 从待审核列表移除
    del PENDING_APPROVALS[req.approval_id]
    
    return {
        "code": 200,
        "message": f"审核结果已提交：{'已批准' if req.approved else '已拒绝'}",
        "data": {
            "approval_id": req.approval_id,
            "status": approval_info.status,
            "approved": req.approved
        }
    }

@router.get("/status/{user_id}/{approval_id}")
async def get_approval_status(user_id: str, approval_id: str):
    """
    查询审核状态
    用于轮询检查审核是否已完成
    """
    # 先检查待审核列表
    if approval_id in PENDING_APPROVALS:
        approval_info = PENDING_APPROVALS[approval_id]
        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": approval_info.status,
                "approval": approval_info.model_dump()
            }
        }
    
    # 再检查历史记录
    if user_id in APPROVAL_HISTORY:
        for info in APPROVAL_HISTORY[user_id]:
            if info.id == approval_id:
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "status": info.status,
                        "approval": info.model_dump()
                    }
                }
    
    return {
        "code": 404,
        "message": "审核请求不存在",
        "data": None
    }

@router.get("/history/{user_id}")
async def get_approval_history(user_id: str):
    """
    获取审核历史记录
    """
    history = APPROVAL_HISTORY.get(user_id, [])
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "total": len(history),
            "history": [info.model_dump() for info in history]
        }
    }

@router.delete("/timeout")
async def cleanup_timeout_approvals():
    """
    清理超时的审核请求
    应由定时任务调用
    """
    now = datetime.now()
    timeout_ids = []
    
    for approval_id, info in PENDING_APPROVALS.items():
        created = datetime.fromisoformat(info.created_at)
        if (now - created).total_seconds() > APPROVAL_TIMEOUT:
            info.status = "timeout"
            info.resolved_at = now.isoformat()
            
            # 移动到历史
            if info.user_id not in APPROVAL_HISTORY:
                APPROVAL_HISTORY[info.user_id] = []
            APPROVAL_HISTORY[info.user_id].append(info)
            
            timeout_ids.append(approval_id)
    
    # 删除超时请求
    for approval_id in timeout_ids:
        del PENDING_APPROVALS[approval_id]
    
    return {
        "code": 200,
        "message": f"已清理 {len(timeout_ids)} 个超时审核请求",
        "data": {"timeout_count": len(timeout_ids)}
    }

@router.get("/tools/high-risk")
async def get_high_risk_tools():
    """
    获取高危工具列表
    """
    return {
        "code": 200,
        "message": "success",
        "data": {
            "tools": list(HIGH_RISK_TOOLS),
            "timeout": APPROVAL_TIMEOUT
        }
    }
