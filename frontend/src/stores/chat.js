import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const userId = ref(localStorage.getItem('userId') || `user_${Date.now()}`)
  const currentConversationId = ref(localStorage.getItem('currentConvId') || null)
  const conversations = ref([])
  const messages = ref([])
  const isLoading = ref(false)
  const mode = ref('chat') // chat, chat-stream, rag, rag-stream, rag-real-stream
  
  // 模式配置
  const modes = [
    { id: 'chat', name: '智能对话', icon: '💬', description: '多智能体协作对话' },
    { id: 'chat-stream', name: '流式对话', icon: '🌊', description: 'SSE 实时流式输出' },
    { id: 'rag', name: 'RAG问答', icon: '📚', description: '知识库检索问答' },
    { id: 'rag-stream', name: 'RAG流式', icon: '📖', description: '知识库流式问答' },
    { id: 'rag-real-stream', name: '真实RAG流式', icon: '📄', description: '逐Token打字机效果' },
    { id: 'plan-execute', name: '任务规划', icon: '📋', description: 'Plan and Execute 任务分解执行' }
  ]
  
  // 当前模式信息
  const currentMode = computed(() => modes.find(m => m.id === mode.value) || modes[0])
  
  // 当前对话标题
  const currentConversationTitle = computed(() => {
    const conv = conversations.value.find(c => c.id === currentConversationId.value)
    return conv?.title || '新对话'
  })
  
  // 添加消息
  const addMessage = (role, content) => {
    const msg = {
      id: Date.now(),
      role,
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(msg)
    
    // 异步保存到数据库
    if (currentConversationId.value) {
      api.addConversationMessage(userId.value, currentConversationId.value, role, content).catch(() => {})
    }
  }
  
  // 更新最后一条消息
  const updateLastMessage = (content) => {
    if (messages.value.length > 0) {
      messages.value[messages.value.length - 1].content = content
    }
  }
  
  // 清空消息（仅前端）
  const clearMessages = () => {
    messages.value = []
  }
  
  // 加载对话列表
  const loadConversations = async () => {
    try {
      const res = await api.getConversationHistory(userId.value)
      conversations.value = res.data.data?.conversations || []
    } catch (error) {
      console.error('加载对话列表失败:', error)
    }
  }
  
  // 新建对话
  const newChat = async () => {
    try {
      const res = await api.createNewConversation(userId.value)
      const conv = res.data.data
      currentConversationId.value = conv.id
      localStorage.setItem('currentConvId', conv.id)
      messages.value = []
      conversations.value.unshift({
        id: conv.id,
        title: conv.title,
        created_at: conv.created_at
      })
      return conv.id
    } catch (error) {
      console.error('创建对话失败:', error)
      return null
    }
  }
  
  // 切换对话
  const switchConversation = async (convId) => {
    if (convId === currentConversationId.value) return
    
    try {
      const res = await api.getConversation(userId.value, convId)
      const data = res.data.data
      currentConversationId.value = convId
      localStorage.setItem('currentConvId', convId)
      messages.value = data.messages || []
      return true
    } catch (error) {
      console.error('切换对话失败:', error)
      return false
    }
  }
  
  // 删除对话
  const deleteConversation = async (convId) => {
    try {
      await api.deleteConversation(userId.value, convId)
      conversations.value = conversations.value.filter(c => c.id !== convId)
      
      // 如果删除的是当前对话，清空消息
      if (convId === currentConversationId.value) {
        currentConversationId.value = null
        localStorage.removeItem('currentConvId')
        messages.value = []
      }
      return true
    } catch (error) {
      console.error('删除对话失败:', error)
      return false
    }
  }
  
  // 清空所有历史
  const clearAllHistory = async () => {
    try {
      await api.clearConversationHistory(userId.value)
      conversations.value = []
      currentConversationId.value = null
      localStorage.removeItem('currentConvId')
      messages.value = []
      return true
    } catch (error) {
      console.error('清空历史失败:', error)
      return false
    }
  }
  
  // 更新对话标题
  const updateTitle = async (convId, title) => {
    try {
      await api.updateConversationTitle(userId.value, convId, title)
      const conv = conversations.value.find(c => c.id === convId)
      if (conv) conv.title = title
    } catch (error) {
      console.error('更新标题失败:', error)
    }
  }
  
  // 切换置顶状态
  const togglePinned = async (convId, pinned) => {
    try {
      await api.toggleConversationPinned(userId.value, convId, pinned)
      const conv = conversations.value.find(c => c.id === convId)
      if (conv) {
        conv.pinned = pinned
        // 重新排序：置顶的排前面
        conversations.value.sort((a, b) => {
          if (a.pinned !== b.pinned) return b.pinned ? 1 : -1
          return new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)
        })
      }
    } catch (error) {
      console.error('置顶操作失败:', error)
    }
  }
  
  // 设置加载状态
  const setLoading = (loading) => {
    isLoading.value = loading
  }
  
  // 设置模式
  const setMode = (newMode) => {
    mode.value = newMode
  }
  
  // 保存用户ID
  const saveUserId = (id) => {
    userId.value = id
    localStorage.setItem('userId', id)
  }
  
  return {
    userId,
    currentConversationId,
    conversations,
    messages,
    isLoading,
    mode,
    modes,
    currentMode,
    currentConversationTitle,
    addMessage,
    updateLastMessage,
    clearMessages,
    loadConversations,
    newChat,
    switchConversation,
    deleteConversation,
    clearAllHistory,
    updateTitle,
    togglePinned,
    setLoading,
    setMode,
    saveUserId
  }
})
