<template>
  <!-- 未登录：显示登录页 -->
  <LoginPage v-if="!isLoggedIn" @login-success="onLoginSuccess" />

  <!-- 已登录：显示主界面 -->
  <div v-else class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="logo">
          <span class="logo-icon">🤖</span>
          <span class="logo-text">LangGraph Agent</span>
        </h1>
      </div>
      
      <!-- 新建对话按钮 -->
      <button class="new-chat-btn" @click="newChat">
        <span>➕</span> 新建对话
        <span class="shortcut-hint">⌘K</span>
      </button>
      
      <!-- 对话历史列表 -->
      <div class="conversation-list">
        <div class="conv-section-header">
          <span>对话历史</span>
          <button v-if="chatStore.conversations.length > 0" class="clear-all-btn" @click="clearAllHistory">
            🗑️ 清空
          </button>
        </div>
        <div class="conv-list">
          <div
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            class="conv-item"
            :class="{ active: conv.id === chatStore.currentConversationId, pinned: conv.pinned }"
            @click="switchConv(conv.id)"
          >
            <span class="conv-icon">{{ conv.pinned ? '📌' : '💬' }}</span>
            <span 
              v-if="editingConvId === conv.id"
              class="conv-title-edit"
              @click.stop
            >
              <input
                v-model="editingTitle"
                @blur="saveTitle(conv.id)"
                @keydown.enter="saveTitle(conv.id)"
                @keydown.escape="cancelEdit"
                ref="editInput"
                autofocus
              />
            </span>
            <span v-else class="conv-title">{{ conv.title }}</span>
            <div class="conv-actions">
              <button class="conv-action-btn" @click.stop="startEdit(conv.id, conv.title)" title="重命名">✏️</button>
              <button class="conv-action-btn" @click.stop="togglePin(conv.id, !conv.pinned)" :title="conv.pinned ? '取消置顶' : '置顶'">{{ conv.pinned ? '📍' : '📌' }}</button>
              <button class="conv-action-btn delete" @click.stop="deleteConv(conv.id)" title="删除">✕</button>
            </div>
          </div>
          <div v-if="chatStore.conversations.length === 0" class="conv-empty">暂无对话历史</div>
        </div>
      </div>
      
      <!-- 功能导航 -->
      <nav class="nav-menu">
        <div class="nav-section">
          <div class="nav-section-title">管理功能</div>
          <button class="nav-item" :class="{ active: activePanel === 'knowledge' }" @click="activePanel = activePanel === 'knowledge' ? 'chat' : 'knowledge'">
            <span class="nav-icon">📚</span>
            <span class="nav-text">知识库管理</span>
          </button>
          <button class="nav-item" :class="{ active: activePanel === 'approval' }" @click="activePanel = activePanel === 'approval' ? 'chat' : 'approval'">
            <span class="nav-icon">✅</span>
            <span class="nav-text">人工审核</span>
          </button>
        </div>
      </nav>
      
      <!-- 底部用户管理 -->
      <div class="sidebar-footer">
        <div class="user-selector" @click="showUserModal = true">
          <span class="user-avatar">{{ currentUserName.charAt(0) }}</span>
          <div class="user-info-text">
            <span class="user-name">{{ currentUserName }}</span>
            <span class="user-hint">点击切换用户</span>
          </div>
          <span class="user-switch-icon">👥</span>
        </div>
        <div class="knowledge-status" @click="knowledgeStore.fetchStatus">
          <span class="status-dot" :class="{ active: knowledgeStore.status.doc_count > 0 }"></span>
          <span>{{ knowledgeStore.status.doc_count }} 文档</span>
        </div>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <template v-if="activePanel === 'chat'"><ChatPanel /></template>
      <template v-else-if="activePanel === 'knowledge'"><KnowledgePanel @close="activePanel = 'chat'" /></template>
      <template v-else-if="activePanel === 'approval'"><ApprovalPanel @close="activePanel = 'chat'" /></template>
    </main>

    <!-- 用户切换弹窗 -->
    <div v-if="showUserModal" class="modal-overlay" @click.self="showUserModal = false">
      <div class="user-modal">
        <div class="user-modal-header">
          <h3>切换用户</h3>
          <button class="btn-icon" @click="showUserModal = false">✕</button>
        </div>
        <div class="user-modal-list">
          <div
            v-for="u in users"
            :key="u.id"
            class="user-modal-item"
            :class="{ active: u.id === chatStore.userId }"
          >
            <span class="user-modal-avatar">{{ (u.name || '?').charAt(0) }}</span>
            <div class="user-modal-info" @click="handleSwitchUser(u)">
              <span class="user-modal-name">{{ u.name || '新用户' }}</span>
              <span v-if="u.id === chatStore.userId" class="user-modal-current">当前</span>
            </div>
            <button
              v-if="u.id !== chatStore.userId"
              class="user-delete-btn"
              @click.stop="handleDeleteUser(u)"
              title="删除用户"
            >✕</button>
          </div>
          <div v-if="users.length === 0" class="user-modal-empty">暂无其他用户</div>
        </div>
        <div class="user-modal-footer">
          <button class="btn btn-danger-outline" @click="handleLogout">退出登录</button>
          <button class="btn btn-secondary" @click="showUserModal = false">取消</button>
        </div>
      </div>
    </div>

    <!-- 切换用户密码验证弹窗 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="password-modal">
        <div class="password-modal-header">
          <h3>验证密码</h3>
          <button class="btn-icon" @click="showPasswordModal = false">✕</button>
        </div>
        <div class="password-modal-body">
          <p class="password-hint">切换到用户 <strong>{{ switchTargetName }}</strong>，请输入该用户的密码</p>
          <input
            v-model="switchPassword"
            type="password"
            class="input"
            placeholder="请输入密码"
            @keydown.enter="confirmSwitchUser"
            ref="passwordInput"
          />
          <div v-if="switchError" class="error-msg">{{ switchError }}</div>
        </div>
        <div class="password-modal-footer">
          <button class="btn btn-secondary" @click="showPasswordModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmSwitchUser">确认切换</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useChatStore } from './stores/chat'
import { useKnowledgeStore } from './stores/knowledge'
import { useApprovalStore } from './stores/approval'
import * as api from './api'
import ChatPanel from './components/ChatPanel.vue'
import KnowledgePanel from './components/KnowledgePanel.vue'
import ApprovalPanel from './components/ApprovalPanel.vue'
import LoginPage from './components/LoginPage.vue'

const chatStore = useChatStore()
const knowledgeStore = useKnowledgeStore()
const approvalStore = useApprovalStore()

const activePanel = ref('chat')
const editingConvId = ref(null)
const editingTitle = ref('')
const editInput = ref(null)

// 登录状态
const isLoggedIn = ref(false)

// 用户管理
const showUserModal = ref(false)
const users = ref([])
const currentUserName = computed(() => {
  const u = users.value.find(u => u.id === chatStore.userId)
  return u?.name || chatStore.userId
})

// 切换用户密码验证
const showPasswordModal = ref(false)
const switchTargetUser = ref(null)
const switchTargetName = ref('')
const switchPassword = ref('')
const switchError = ref('')
const passwordInput = ref(null)

// 登录成功
const onLoginSuccess = async (userData) => {
  isLoggedIn.value = true
  chatStore.saveUserId(userData.id)
  localStorage.setItem('userName', userData.name)
  
  // 加载数据
  await Promise.all([
    loadUsers(),
    chatStore.loadConversations(),
    knowledgeStore.fetchStatus(),
    approvalStore.fetchPendingApprovals(chatStore.userId)
  ])
}

// 退出登录
const handleLogout = () => {
  if (!confirm('确定退出登录吗？')) return
  isLoggedIn.value = false
  chatStore.clearMessages()
  chatStore.conversations = []
  chatStore.currentConversationId = null
  localStorage.removeItem('userId')
  localStorage.removeItem('userName')
  showUserModal.value = false
}

// 加载用户列表
const loadUsers = async () => {
  try {
    const res = await api.getUsers()
    users.value = res.data.data?.users || []
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

// 点击切换用户 → 弹出密码框
const handleSwitchUser = (user) => {
  if (user.id === chatStore.userId) {
    showUserModal.value = false
    return
  }
  switchTargetUser.value = user
  switchTargetName.value = user.name
  switchPassword.value = ''
  switchError.value = ''
  showPasswordModal.value = false
  showUserModal.value = false
  
  nextTick(() => {
    showPasswordModal.value = true
    nextTick(() => passwordInput.value?.focus())
  })
}

// 确认切换用户（验证密码）
const confirmSwitchUser = async () => {
  switchError.value = ''
  if (!switchPassword.value) {
    switchError.value = '请输入密码'
    return
  }

  try {
    const res = await api.authVerify(switchTargetUser.value.id, switchPassword.value)
    if (res.data.code === 200) {
      // 密码正确，切换用户
      chatStore.saveUserId(switchTargetUser.value.id)
      chatStore.clearMessages()
      chatStore.currentConversationId = null
      showPasswordModal.value = false

      await Promise.all([
        loadUsers(),
        chatStore.loadConversations(),
        approvalStore.fetchPendingApprovals(chatStore.userId)
      ])
    } else {
      switchError.value = res.data.message
    }
  } catch (error) {
    switchError.value = '验证失败'
  }
}

// 删除用户
const handleDeleteUser = async (user) => {
  if (!confirm(`确定删除用户「${user.name}」吗？该用户的所有对话历史也将被删除！`)) {
    return
  }

  try {
    const res = await api.deleteUser(user.id)
    if (res.data.code === 200) {
      // 刷新用户列表
      await loadUsers()
    } else {
      alert('删除失败：' + res.data.message)
    }
  } catch (error) {
    alert('删除失败，请检查网络')
  }
}

// 对话管理
const newChat = async () => {
  await chatStore.newChat()
  activePanel.value = 'chat'
}

const switchConv = async (convId) => {
  await chatStore.switchConversation(convId)
  activePanel.value = 'chat'
}

const deleteConv = async (convId) => {
  if (confirm('确定删除该对话吗？')) {
    await chatStore.deleteConversation(convId)
  }
}

const clearAllHistory = async () => {
  if (confirm('确定清空所有对话历史吗？此操作不可恢复！')) {
    await chatStore.clearAllHistory()
  }
}

const startEdit = async (convId, title) => {
  editingConvId.value = convId
  editingTitle.value = title
  await nextTick()
  const inputs = document.querySelectorAll('.conv-title-edit input')
  if (inputs.length > 0) {
    inputs[inputs.length - 1].focus()
    inputs[inputs.length - 1].select()
  }
}

const saveTitle = async (convId) => {
  if (editingTitle.value.trim()) {
    await chatStore.updateTitle(convId, editingTitle.value.trim())
  }
  editingConvId.value = null
}

const cancelEdit = () => {
  editingConvId.value = null
}

const togglePin = async (convId, pinned) => {
  await chatStore.togglePinned(convId, pinned)
}

// 初始化：检查是否已登录
onMounted(async () => {
  const savedUserId = localStorage.getItem('userId')
  const savedUserName = localStorage.getItem('userName')
  
  if (savedUserId && savedUserName) {
    // 尝试验证（通过获取用户列表确认用户存在）
    try {
      await loadUsers()
      const userExists = users.value.find(u => u.id === savedUserId)
      if (userExists) {
        isLoggedIn.value = true
        chatStore.saveUserId(savedUserId)
        
        await Promise.all([
          chatStore.loadConversations(),
          knowledgeStore.fetchStatus(),
          approvalStore.fetchPendingApprovals(savedUserId)
        ])
        
        if (chatStore.currentConversationId) {
          await chatStore.switchConversation(chatStore.currentConversationId)
        }
      }
    } catch (error) {
      console.error('自动登录失败:', error)
      // 验证失败，清除无效的登录信息
      localStorage.removeItem('userId')
      localStorage.removeItem('userName')
    }
  }
  
  // 监听全局快捷键
  window.addEventListener('keydown', handleGlobalKeydown)
})

// 全局快捷键处理
const handleGlobalKeydown = (e) => {
  // Command+K (Mac) 或 Ctrl+K (Windows/Linux) 新建会话
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    if (isLoggedIn.value) {
      newChat()
    }
  }
}
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100%;
}

/* ==================== 侧边栏 ==================== */
.sidebar {
  width: 260px;
  background-color: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.logo-icon { font-size: 24px; }
.logo-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.new-chat-btn {
  margin: 12px;
  padding: 12px 16px;
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  transition: all 0.2s ease;
}
.new-chat-btn:hover { background-color: var(--bg-input); }

.shortcut-hint {
  font-size: 11px;
  color: var(--text-muted);
  background-color: var(--bg-input);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  border-bottom: 1px solid var(--border-color);
  max-height: 300px;
}

.conv-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
}

.clear-all-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}
.clear-all-btn:hover { background-color: var(--bg-input); color: var(--danger-color); }

.conv-list { display: flex; flex-direction: column; gap: 2px; }

.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.conv-item:hover { background-color: var(--bg-input); }
.conv-item.active { background-color: var(--primary-color); color: white; }
.conv-item.pinned { background-color: rgba(255, 193, 7, 0.1); border-left: 3px solid var(--warning-color); }
.conv-item.pinned.active { background-color: var(--primary-color); border-left-color: transparent; }

.conv-icon { font-size: 14px; }
.conv-title { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-title-edit { flex: 1; }
.conv-title-edit input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid var(--primary-color);
  border-radius: 4px;
  background-color: var(--bg-dark);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}

.conv-actions { display: flex; gap: 2px; opacity: 0; transition: opacity 0.2s ease; }
.conv-item:hover .conv-actions { opacity: 1; }
.conv-action-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  line-height: 1;
}
.conv-action-btn:hover { background-color: var(--bg-input); color: var(--text-primary); }
.conv-action-btn.delete:hover { background-color: var(--danger-color); color: white; }

.conv-empty { padding: 16px; text-align: center; color: var(--text-muted); font-size: 12px; }

.nav-menu { overflow-y: auto; padding: 8px; }
.nav-section { margin-bottom: 16px; }
.nav-section-title { padding: 8px 12px; font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }

.nav-item {
  width: 100%;
  padding: 10px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.2s ease;
}
.nav-item:hover { background-color: var(--bg-input); color: var(--text-primary); }
.nav-item.active { background-color: var(--bg-input); color: var(--text-primary); }
.nav-icon { font-size: 18px; }
.nav-text { flex: 1; text-align: left; }

/* 侧边栏底部 */
.sidebar-footer { padding: 12px; border-top: 1px solid var(--border-color); }

.user-selector {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background-color: var(--bg-input);
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-bottom: 8px;
}
.user-selector:hover { background-color: var(--border-color); }

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #2dd4bf;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-info-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.user-name { font-size: 14px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-hint { font-size: 11px; color: var(--text-muted); }
.user-switch-icon { font-size: 18px; opacity: 0.6; }

.knowledge-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}
.knowledge-status:hover { color: var(--text-primary); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background-color: var(--text-muted); }
.status-dot.active { background-color: var(--success-color); }

.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* ==================== 弹窗通用 ==================== */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.btn-icon {
  background: none;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
}

/* ==================== 用户切换弹窗 ==================== */
.user-modal {
  background-color: #1a1a2e;
  border-radius: 16px;
  width: 420px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.user-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
}
.user-modal-header h3 { font-size: 18px; font-weight: 600; color: white; }

.user-modal-list { flex: 1; overflow-y: auto; padding: 0 16px; max-height: 300px; }

.user-modal-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-bottom: 4px;
}
.user-modal-item:hover { background-color: rgba(255, 255, 255, 0.08); }
.user-modal-item.active { background-color: #1e293b; }

.user-modal-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background-color: #2dd4bf; color: white;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 600; flex-shrink: 0;
}

.user-modal-info { flex: 1; display: flex; align-items: center; gap: 10px; cursor: pointer; }
.user-modal-name { font-size: 15px; font-weight: 500; color: white; }
.user-modal-current { font-size: 12px; color: #2dd4bf; background-color: rgba(45, 212, 191, 0.15); padding: 2px 8px; border-radius: 10px; }
.user-modal-empty { padding: 32px; text-align: center; font-size: 14px; color: rgba(255, 255, 255, 0.4); }

.user-delete-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  transition: all 0.2s ease;
}
.user-delete-btn:hover {
  background-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.user-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

/* ==================== 密码验证弹窗 ==================== */
.password-modal {
  background-color: #1a1a2e;
  border-radius: 16px;
  width: 380px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.password-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
}
.password-modal-header h3 { font-size: 18px; font-weight: 600; color: white; }

.password-modal-body { padding: 0 24px 20px; }
.password-hint { font-size: 14px; color: rgba(255, 255, 255, 0.6); margin-bottom: 16px; }
.password-hint strong { color: #2dd4bf; }

.password-modal-body .input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  background-color: rgba(255, 255, 255, 0.05);
  color: white;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.password-modal-body .input:focus { border-color: #2dd4bf; }
.password-modal-body .input::placeholder { color: rgba(255, 255, 255, 0.3); }

.error-msg {
  padding: 8px 12px;
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 13px;
  margin-top: 12px;
}

.password-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 0 24px 20px;
}

/* ==================== 按钮 ==================== */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-primary { background-color: #2dd4bf; color: #1a1a2e; }
.btn-primary:hover { background-color: #14b8a6; }
.btn-secondary { background-color: rgba(255, 255, 255, 0.1); color: white; }
.btn-secondary:hover { background-color: rgba(255, 255, 255, 0.15); }
.btn-danger-outline { background: transparent; border: 1px solid #ef4444; color: #ef4444; }
.btn-danger-outline:hover { background-color: #ef4444; color: white; }
</style>
