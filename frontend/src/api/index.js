import axios from 'axios'

const API_BASE = ''

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// ==================== 对话相关 API ====================

// 普通对话
export const chat = (userId, query) => {
  return api.post('/chat', { user_id: userId, query })
}

// SSE 流式对话
export const chatStream = (userId, query) => {
  return fetchSSE(`${API_BASE}/chat/stream`, { user_id: userId, query })
}

// ==================== RAG 相关 API ====================

// RAG 问答
export const ragQuery = (userId, query) => {
  return api.post('/rag', { user_id: userId, query })
}

// RAG 流式问答
export const ragStream = (userId, query) => {
  return fetchSSE(`${API_BASE}/rag/stream`, { user_id: userId, query })
}

// 真实 RAG 流式问答
export const ragRealStream = (userId, query) => {
  return fetchSSE(`${API_BASE}/rag/real/stream`, { user_id: userId, query })
}

// ==================== 通用 SSE 请求 ====================

async function* fetchSSE(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          yield data
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}

// ==================== 知识库管理 API ====================

// 更新知识库
export const updateKnowledge = (userId, isIncremental = true) => {
  return api.post('/knowledge/update', {
    user_id: userId,
    is_incremental: isIncremental
  })
}

// 获取知识库状态
export const getKnowledgeStatus = () => {
  return api.get('/api/knowledge/status')
}

// 构建知识图谱
export const buildKnowledgeGraph = () => {
  return api.post('/api/knowledge/graph/build')
}

// ==================== 用户认证 API ====================

// 用户注册
export const authRegister = (name, password) => {
  return api.post('/api/auth/register', { name, password })
}

// 用户登录
export const authLogin = (name, password) => {
  return api.post('/api/auth/login', { name, password })
}

// 验证密码（切换用户）
export const authVerify = (userId, password) => {
  return api.post('/api/auth/verify', { user_id: userId, password })
}

// 重置密码（忘记密码）
export const resetPassword = (name, newPassword) => {
  return api.post('/api/auth/reset-password', { name, new_password: newPassword })
}

// 修改密码
export const changePassword = (userId, oldPassword, newPassword) => {
  return api.put(`/api/users/${userId}/password`, { old_password: oldPassword, new_password: newPassword })
}

// ==================== 用户管理 API ====================

// 获取所有用户
export const getUsers = () => {
  return api.get('/api/users')
}

// 修改用户名
export const updateUser = (userId, name) => {
  return api.put(`/api/users/${userId}`, { name })
}

// 删除用户
export const deleteUser = (userId) => {
  return api.delete(`/api/users/${userId}`)
}

// 记录用户登录
export const userLogin = (userId) => {
  return api.post(`/api/users/${userId}/login`)
}

// ==================== 会话管理 API ====================

// 获取会话列表
export const getConversationHistory = (userId) => {
  return api.get(`/api/history/${userId}`)
}

// 创建新会话
export const createNewConversation = (userId) => {
  return api.post(`/api/conversation/new/${userId}`)
}

// 获取会话详情
export const getConversation = (userId, convId) => {
  return api.get(`/api/conversation/${userId}/${convId}`)
}

// 添加消息到对话
export const addConversationMessage = (userId, convId, role, content) => {
  return api.post(`/api/conversation/${userId}/${convId}/message`, { role, content })
}

// 更新对话标题
export const updateConversationTitle = (userId, convId, title) => {
  return api.put(`/api/conversation/${userId}/${convId}/title`, { title })
}

// 设置/取消置顶
export const toggleConversationPinned = (userId, convId, pinned) => {
  return api.put(`/api/conversation/${userId}/${convId}/pinned`, { pinned })
}

// 删除单个对话
export const deleteConversation = (userId, convId) => {
  return api.delete(`/api/conversation/${userId}/${convId}`)
}

// 清空会话历史
export const clearConversationHistory = (userId) => {
  return api.delete(`/api/history/${userId}`)
}

// ==================== 人工审核 API ====================

// 创建审核请求
export const createApprovalRequest = (data) => {
  return api.post('/api/approval/request', data)
}

// 获取待审核列表
export const getPendingApprovals = (userId) => {
  return api.get(`/api/approval/pending/${userId}`)
}

// 提交审核结果
export const submitApproval = (userId, approvalId, approved, comment = '') => {
  return api.post('/api/approval/submit', {
    user_id: userId,
    approval_id: approvalId,
    approved,
    reason: comment
  })
}

// 获取审核历史
export const getApprovalHistory = (userId, limit = 50) => {
  return api.get(`/api/approval/history/${userId}`, { params: { limit } })
}

// 获取审核详情
export const getApprovalDetail = (userId, approvalId) => {
  return api.get(`/api/approval/${approvalId}`, { params: { user_id: userId } })
}

// 清理超时审核
export const cleanupTimeoutApprovals = () => {
  return api.post('/api/approval/cleanup')
}

// 获取高危工具列表
export const getHighRiskTools = () => {
  return api.get('/api/approval/high-risk-tools')
}

// 检查当前会话是否需要人工审核（interrupt 状态）
export const checkApprovalStatus = (userId) => {
  return api.get(`/api/approval/check/${userId}`)
}

// 审核后恢复工作流
export const resumeAfterApproval = (userId, threadId, approved) => {
  return api.post('/api/approval/resume', {
    user_id: userId,
    thread_id: threadId,
    approved
  })
}
