<template>
  <div class="knowledge-panel">
    <!-- 头部 -->
    <header class="panel-header">
      <div class="header-info">
        <span class="header-icon">📚</span>
        <h2>知识库管理</h2>
      </div>
      <button class="btn-icon" @click="$emit('close')">✕</button>
    </header>
    
    <!-- 内容 -->
    <div class="panel-content">
      <!-- 知识库状态卡片 -->
      <div class="card status-card">
        <div class="card-header">
          <h3 class="card-title">📊 知识库状态</h3>
          <button class="btn-small btn-secondary" @click="knowledgeStore.fetchStatus">
            刷新
          </button>
        </div>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-value">{{ knowledgeStore.status.doc_count }}</div>
            <div class="status-label">文档数量</div>
          </div>
          <div class="status-item">
            <div class="status-value">{{ knowledgeStore.status.vector_db }}</div>
            <div class="status-label">向量数据库</div>
          </div>
          <div class="status-item">
            <div class="status-value">{{ knowledgeStore.status.graph_db }}</div>
            <div class="status-label">图数据库</div>
          </div>
          <div class="status-item">
            <div class="status-value">{{ formatDate(knowledgeStore.status.last_update) || '未更新' }}</div>
            <div class="status-label">最后更新</div>
          </div>
        </div>
      </div>
      
      <!-- 操作卡片 -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">🔄 知识库操作</h3>
        </div>
        <div class="action-buttons">
          <button 
            class="btn btn-primary" 
            :disabled="knowledgeStore.isLoading"
            @click="handleIncrementalUpdate"
          >
            <span v-if="!knowledgeStore.isLoading">➕ 增量更新</span>
            <span v-else>更新中...</span>
          </button>
          <button 
            class="btn btn-secondary" 
            :disabled="knowledgeStore.isLoading"
            @click="handleFullUpdate"
          >
            <span v-if="!knowledgeStore.isLoading">🔄 全量重建</span>
            <span v-else>重建中...</span>
          </button>
          <button 
            class="btn btn-secondary" 
            :disabled="knowledgeStore.isLoading"
            @click="handleBuildGraph"
          >
            <span v-if="!knowledgeStore.isLoading">🕸️ 构建图谱</span>
            <span v-else>构建中...</span>
          </button>
        </div>
        <p class="action-hint">
          💡 增量更新会保留历史数据，全量重建会清空所有数据后重新导入
        </p>
      </div>
      
      <!-- 消息提示 -->
      <div v-if="knowledgeStore.lastMessage" class="message-card" :class="messageClass">
        {{ knowledgeStore.lastMessage }}
      </div>
      
      <!-- 文档目录说明 -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">📁 文档目录</h3>
        </div>
        <div class="doc-info">
          <p>将文档放入以下目录后，点击"增量更新"即可导入知识库：</p>
          <code class="doc-path">./rag/docs/</code>
          <p class="doc-formats">支持的格式：.txt, .md, .pdf</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'
import { useChatStore } from '../stores/chat'

const emit = defineEmits(['close'])

const knowledgeStore = useKnowledgeStore()
const chatStore = useChatStore()

// 消息样式
const messageClass = computed(() => {
  const msg = knowledgeStore.lastMessage
  if (msg.includes('✅')) return 'success'
  if (msg.includes('❌')) return 'error'
  return 'info'
})

// 增量更新
const handleIncrementalUpdate = async () => {
  try {
    await knowledgeStore.updateIncremental(chatStore.userId)
  } catch (error) {
    console.error(error)
  }
}

// 全量重建
const handleFullUpdate = async () => {
  if (!confirm('⚠️ 全量重建会清空所有历史数据，确定要继续吗？')) {
    return
  }
  try {
    await knowledgeStore.updateFull(chatStore.userId)
  } catch (error) {
    console.error(error)
  }
}

// 构建知识图谱
const handleBuildGraph = async () => {
  try {
    await knowledgeStore.buildGraph()
  } catch (error) {
    console.error(error)
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return null
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.knowledge-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-dark);
}

/* 头部 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 28px;
}

.header-info h2 {
  font-size: 18px;
  font-weight: 600;
}

/* 内容 */
.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

/* 状态卡片 */
.status-card {
  margin-bottom: 20px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.status-item {
  text-align: center;
  padding: 16px;
  background-color: var(--bg-dark);
  border-radius: 8px;
}

.status-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 4px;
}

.status-label {
  font-size: 12px;
  color: var(--text-muted);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.action-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* 消息卡片 */
.message-card {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.message-card.success {
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--success-color);
  color: var(--success-color);
}

.message-card.error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--danger-color);
  color: var(--danger-color);
}

.message-card.info {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid var(--info-color);
  color: var(--info-color);
}

/* 文档信息 */
.doc-info {
  font-size: 14px;
  line-height: 1.8;
}

.doc-path {
  display: block;
  padding: 8px 12px;
  background-color: var(--bg-dark);
  border-radius: 6px;
  margin: 12px 0;
  font-family: monospace;
  color: var(--primary-color);
}

.doc-formats {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
