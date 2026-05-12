<template>
  <div class="chat-panel">
    <!-- 头部 -->
    <header class="chat-header">
      <div class="header-left">
        <h2>{{ chatStore.currentConversationTitle }}</h2>
      </div>
      <button class="btn-icon" @click="clearChat" title="清空对话">
        🗑️
      </button>
    </header>
    
    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesContainer">
      <!-- 欢迎消息 -->
      <div v-if="chatStore.messages.length === 0" class="welcome-message">
        <div class="welcome-icon">🤖</div>
        <h2>欢迎使用 LangGraph 多智能体助手</h2>
        <p>选择下方模式开始体验</p>
        <div class="quick-actions">
          <button 
            v-for="action in quickActions" 
            :key="action.text"
            class="quick-action-btn"
            @click="sendQuickMessage(action.text)"
          >
            {{ action.icon }} {{ action.text }}
          </button>
        </div>
      </div>
      
      <!-- 消息列表 -->
      <div v-else class="messages-list">
        <!-- Plan-Execute 面板（独立渲染，不显示普通消息列表） -->
        <PlanExecutePanel v-if="chatStore.mode === 'plan-execute'" />
        
        <!-- 非 Plan-Execute 模式的消息列表 -->
        <template v-else>
        <div 
          v-for="msg in chatStore.messages" 
          :key="msg.id"
          class="message"
          :class="`message-${msg.role}`"
        >
          <div class="message-header">
            <div class="message-avatar" :class="msg.role">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <span class="message-role">
              {{ msg.role === 'user' ? '你' : '助手' }}
            </span>
            <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
        </div>
        </template>
        
        <!-- 加载中状态 -->
        <div v-if="chatStore.isLoading" class="message message-assistant">
          <div class="message-header">
            <div class="message-avatar assistant">🤖</div>
            <span class="message-role">助手</span>
          </div>
          <div class="message-content">
            <div class="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span style="margin-left: 8px; color: var(--text-muted);">思考中...</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 模式选择器 -->
      <div class="mode-selector">
        <button
          v-for="m in chatStore.modes"
          :key="m.id"
          class="mode-btn"
          :class="{ active: chatStore.mode === m.id }"
          @click="chatStore.setMode(m.id)"
          :title="m.description"
        >
          <span class="mode-icon">{{ m.icon }}</span>
          <span class="mode-name">{{ m.name }}</span>
        </button>
      </div>
      
      <div class="input-container">
        <textarea
          v-model="inputText"
          class="input chat-input"
          placeholder="输入你的问题..."
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.enter.shift="inputText += '\n'"
          :disabled="chatStore.isLoading"
          rows="1"
          ref="inputRef"
        ></textarea>
        <button 
          class="send-btn"
          :disabled="!inputText.trim() || chatStore.isLoading"
          @click="sendMessage"
        >
          <span v-if="!chatStore.isLoading">发送</span>
          <span v-else class="loading-dots"><span></span><span></span><span></span></span>
        </button>
      </div>
      <div class="input-hint">
        <span>按 Enter 发送，Shift + Enter 换行</span>
        <span v-if="chatStore.mode.includes('stream')">• 流式输出中</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { usePlanExecuteStore } from '../stores/planExecute.js'
import PlanExecutePanel from './PlanExecutePanel.vue'
import * as api from '../api'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const chatStore = useChatStore()
const planExecuteStore = usePlanExecuteStore()

const inputText = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

// 快捷操作
const quickActions = [
  { icon: '💡', text: '介绍一下你自己' },
  { icon: '📚', text: '知识库有什么内容' },
  { icon: '🔍', text: '帮我搜索最新AI资讯' }
]

// 发送快捷消息
const sendQuickMessage = (text) => {
  inputText.value = text
  sendMessage()
}

// 发送消息
const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || chatStore.isLoading) return
  
  // 如果没有当前对话，先创建一个
  if (!chatStore.currentConversationId) {
    await chatStore.newChat()
  }
  
  // 添加用户消息
  chatStore.addMessage('user', text)
  inputText.value = ''
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
  
  // 设置加载状态
  chatStore.setLoading(true)
  
  try {
    let response = ''
    
    // 根据模式选择不同的API
    switch (chatStore.mode) {
      case 'chat':
        // 普通对话
        const chatRes = await api.chat(chatStore.userId, text)
        response = chatRes.data.reply
        chatStore.addMessage('assistant', response)
        
        // 检查是否需要人工审核
        await checkAndHandleApproval()
        break
        
      case 'chat-stream':
        // SSE 流式对话
        chatStore.addMessage('assistant', '')
        let streamNeedsApproval = false
        let streamToolInfo = ''
        for await (const data of api.chatStream(chatStore.userId, text)) {
          if (data.type === 'status') {
            // 状态提示（正在思考/正在调用工具）
            chatStore.updateLastMessage(`⏳ ${data.content}`)
            scrollToBottom()
          } else if (data.type === 'ai') {
            response += data.content
            chatStore.updateLastMessage(response)
            scrollToBottom()
          } else if (data.type === 'done') {
            if (data.needs_approval) {
              streamNeedsApproval = true
              streamToolInfo = data.tool_info || '未知工具'
            }
          }
        }
        
        if (streamNeedsApproval) {
          handleApprovalNeeded(streamToolInfo)
        }
        break
        
      case 'rag':
        // RAG 问答
        const ragRes = await api.ragQuery(chatStore.userId, text)
        response = ragRes.data.reply
        chatStore.addMessage('assistant', response)
        break
        
      case 'rag-stream':
        // RAG 流式
        chatStore.addMessage('assistant', '')
        for await (const data of api.ragStream(chatStore.userId, text)) {
          if (data.type === 'ai') {
            response += data.content
            chatStore.updateLastMessage(response)
            scrollToBottom()
          }
        }
        break
        
      case 'rag-real-stream':
        // 真实 RAG 流式
        chatStore.addMessage('assistant', '')
        for await (const data of api.ragRealStream(chatStore.userId, text)) {
          if (data.type === 'ai') {
            response += data.content
            chatStore.updateLastMessage(response)
            scrollToBottom()
          }
        }
        break
        
      case 'plan-execute':
        // Plan and Execute 模式（不添加空助手消息，由 PlanExecutePanel 独立渲染）
        
        // 执行 Plan-Execute
        await planExecuteStore.execute(chatStore.userId, text, (type, data) => {
          if (type === 'step_completed') {
            // 更新消息显示进度
            const progress = `步骤 ${data.step_index}/${planExecuteStore.totalSteps} 完成`
            chatStore.updateLastMessage(`⏳ ${progress}\n\n正在执行: ${data.step}`)
            scrollToBottom()
          } else if (type === 'final_response') {
            // 最终回答
            response = data.response
            chatStore.updateLastMessage(response)
            scrollToBottom()
          } else if (type === 'error') {
            response = `❌ 执行失败: ${data.error}`
            chatStore.updateLastMessage(response)
            scrollToBottom()
          }
        })
        
        // 如果执行成功但没有通过回调设置响应，使用 store 中的结果
        if (!response && planExecuteStore.finalResponse) {
          response = planExecuteStore.finalResponse
          chatStore.updateLastMessage(response)
        }
        break
    }
    
    // 更新对话标题（如果是第一条消息）
    if (chatStore.messages.length === 2) {
      const firstUserMsg = chatStore.messages.find(m => m.role === 'user')
      if (firstUserMsg) {
        const title = firstUserMsg.content.slice(0, 20) + (firstUserMsg.content.length > 20 ? '...' : '')
        chatStore.updateTitle(chatStore.currentConversationId, title)
      }
    }
  } catch (error) {
    chatStore.addMessage('assistant', `❌ 请求失败: ${error.message}`)
  } finally {
    chatStore.setLoading(false)
    await nextTick()
    scrollToBottom()
    inputRef.value?.focus()
  }
}

// 处理需要人工审核
const handleApprovalNeeded = (toolInfo) => {
  const info = toolInfo || '未知工具'
  chatStore.addMessage('assistant', `⏳ 等待人工审核中...\n\n工具调用：${info}\n\n请在左侧「人工审核」面板中处理此请求。`)
  
  // 通知父组件显示审核徽章 + 自动刷新审核面板
  window.dispatchEvent(new CustomEvent('approval-needed', {
    detail: { tool_info: info, thread_id: chatStore.userId }
  }))
}

// 检查并处理人工审核（普通模式用，通过 API 检查）
const checkAndHandleApproval = async () => {
  try {
    const checkRes = await api.checkApprovalStatus(chatStore.userId)
    const data = checkRes.data.data
    
    if (data && data.needs_approval) {
      handleApprovalNeeded(data.tool_info)
    }
  } catch (error) {
    // 检查审核状态失败不影响主流程
    console.log('审核状态检查跳过:', error.message)
  }
}

// 清空对话
const clearChat = () => {
  if (confirm('确定要清空当前对话吗？')) {
    chatStore.clearMessages()
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 滚动到底部（平滑滚动）
const scrollToBottomSmooth = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTo({
      top: messagesContainer.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 渲染 Markdown（使用 DOMPurify 防止 XSS 攻击）
const renderMarkdown = (content) => {
  try {
    return DOMPurify.sanitize(marked(content))
  } catch {
    return content
  }
}

// 监听消息变化自动滚动
watch(() => chatStore.messages.length, () => {
  nextTick(scrollToBottomSmooth)
})

// 监听最后一条消息内容变化（流式输出时）
watch(
  () => chatStore.messages.length > 0 ? chatStore.messages[chatStore.messages.length - 1].content : '',
  () => {
    nextTick(scrollToBottom)
  }
)

// 监听审核恢复后的回复
const onApprovalReply = (event) => {
  const reply = event.detail?.reply
  if (reply) {
    chatStore.addMessage('assistant', `✅ 审核已处理，工作流恢复执行：\n\n${reply}`)
    nextTick(scrollToBottom)
  }
}

onMounted(() => {
  window.addEventListener('approval-reply', onApprovalReply)
})

onUnmounted(() => {
  window.removeEventListener('approval-reply', onApprovalReply)
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 头部 */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-dark);
}

.header-left h2 {
  font-size: 16px;
  font-weight: 600;
}

/* 消息容器 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

/* 欢迎消息 */
.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-secondary);
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.welcome-message h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.welcome-message p {
  font-size: 16px;
  margin-bottom: 32px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.quick-action-btn {
  padding: 12px 20px;
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-action-btn:hover {
  background-color: var(--border-color);
  transform: translateY(-2px);
}

/* 消息列表 */
.messages-list {
  max-width: 800px;
  margin: 0 auto;
}

.message {
  margin-bottom: 16px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.message-avatar.user {
  background-color: var(--primary-color);
}

.message-avatar.assistant {
  background-color: var(--info-color);
}

.message-role {
  font-weight: 600;
  font-size: 14px;
}

.message-time {
  font-size: 12px;
  color: var(--text-muted);
}

.message-content {
  padding-left: 48px;
  line-height: 1.6;
  color: var(--text-primary);
}

/* 表格样式 */
.message-content :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 16px 0;
  font-size: 13px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.message-content :deep(thead tr) {
  background: linear-gradient(90deg, #2a9d8f, #7b8cde);
}

.message-content :deep(th) {
  color: #ffffff;
  font-weight: 600;
  text-align: left;
  padding: 14px 20px;
  border: none;
}

.message-content :deep(td) {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  vertical-align: top;
}

.message-content :deep(td:last-child) {
  border-right: none;
}

.message-content :deep(tr:last-child td) {
  border-bottom: none;
}

.message-content :deep(tbody tr:nth-child(odd)) {
  background-color: #2a2a3a;
}

.message-content :deep(tbody tr:nth-child(even)) {
  background-color: #1f1f2a;
}

.message-content :deep(tbody tr:hover td) {
  background-color: rgba(255, 255, 255, 0.05);
}

.message-content :deep(th:first-child),
.message-content :deep(td:first-child) {
  white-space: nowrap;
  font-weight: 500;
}

/* 列表样式优化 */
.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.message-content :deep(li) {
  margin: 4px 0;
}

/* 标题样式 */
.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3),
.message-content :deep(h4) {
  margin: 16px 0 8px;
  color: var(--text-primary);
}

.message-content :deep(h1) { font-size: 1.5em; }
.message-content :deep(h2) { font-size: 1.3em; }
.message-content :deep(h3) { font-size: 1.1em; }

/* 代码块样式 */
.message-content :deep(pre) {
  background-color: var(--bg-input);
  border-radius: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-content :deep(code) {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.message-content :deep(p code) {
  background-color: var(--bg-input);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 输入区域 */
.input-area {
  padding: 12px 24px 16px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-dark);
}

/* 模式选择器 */
.mode-selector {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn:hover {
  background-color: var(--border-color);
  color: var(--text-primary);
}

.mode-btn.active {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.mode-icon {
  font-size: 14px;
}

.mode-name {
  font-weight: 500;
}

.input-container {
  display: flex;
  gap: 12px;
  max-width: 800px;
  margin: 0 auto;
}

.chat-input {
  flex: 1;
  resize: none;
  min-height: 52px;
  max-height: 200px;
  padding: 14px 16px;
}

.send-btn {
  padding: 0 24px;
  background-color: var(--primary-color);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background-color: var(--primary-hover);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-hint {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}
</style>
