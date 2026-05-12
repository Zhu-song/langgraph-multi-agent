<template>
  <div class="approval-panel">
    <!-- 头部 -->
    <header class="panel-header">
      <div class="header-info">
        <span class="header-icon">✅</span>
        <h2>人工审核</h2>
        <span v-if="totalPendingCount > 0" class="pending-count">
          {{ totalPendingCount }} 待审核
        </span>
      </div>
      <div class="header-actions">
        <button class="btn-small btn-secondary" @click="refreshData">
          🔄 刷新
        </button>
        <button class="btn-icon" @click="$emit('close')">✕</button>
      </div>
    </header>

    <!-- 内容 -->
    <div class="panel-content">
      <!-- 标签页切换 -->
      <div class="tabs">
        <button
          class="tab"
          :class="{ active: activeTab === 'pending' }"
          @click="activeTab = 'pending'"
        >
          待审核
          <span v-if="totalPendingCount > 0" class="tab-badge">
            {{ totalPendingCount }}
          </span>
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'history' }"
          @click="activeTab = 'history'"
        >
          审核历史
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'create' }"
          @click="activeTab = 'create'"
        >
          创建请求
        </button>
      </div>

      <!-- 待审核列表 -->
      <div v-if="activeTab === 'pending'" class="tab-content">
        <div v-if="approvalStore.isLoading && approvalStore.pendingApprovals.length === 0 && !workflowPending" class="loading-state">
          <div class="loading-dots"><span></span><span></span><span></span></div>
          <span>加载中...</span>
        </div>

        <div v-else-if="totalPendingCount === 0" class="empty-state">
          <div class="empty-state-icon">📭</div>
          <div class="empty-state-text">暂无待审核请求</div>
        </div>

        <div v-else class="approval-list">
          <!-- 工作流 interrupt 待审核项（优先显示） -->
          <div
            v-if="workflowPending"
            class="approval-card workflow-interrupt-card"
          >
            <div class="approval-header">
              <div class="approval-id">⚡ 工作流拦截</div>
              <span class="tag tag-warning">待审核</span>
            </div>
            <div class="approval-body">
              <div class="approval-item">
                <span class="label">拦截原因：</span>
                <span class="value">{{ workflowPending.tool_info }}</span>
              </div>
              <div class="approval-item">
                <span class="label">来源：</span>
                <span class="value">LangGraph 工作流 interrupt</span>
              </div>
              <div class="approval-item">
                <span class="label">会话ID：</span>
                <span class="value">{{ workflowPending.thread_id }}</span>
              </div>
            </div>
            <div class="approval-actions">
              <button
                class="btn btn-primary btn-small"
                @click="handleWorkflowApprove"
              >
                ✅ 通过
              </button>
              <button
                class="btn btn-danger btn-small"
                @click="handleWorkflowReject"
              >
                ❌ 拒绝
              </button>
            </div>
          </div>

          <!-- 旧审核系统的待审核项 -->
          <div
            v-for="approval in approvalStore.pendingApprovals"
            :key="approval.id"
            class="approval-card"
          >
            <div class="approval-header">
              <div class="approval-id">#{{ approval.id.slice(0, 8) }}</div>
              <span class="tag tag-warning">待审核</span>
            </div>
            <div class="approval-body">
              <div class="approval-item">
                <span class="label">工具名称：</span>
                <span class="value">{{ approval.tool_name }}</span>
              </div>
              <div class="approval-item">
                <span class="label">请求用户：</span>
                <span class="value">{{ approval.user_id }}</span>
              </div>
              <div class="approval-item">
                <span class="label">请求时间：</span>
                <span class="value">{{ formatDate(approval.created_at) }}</span>
              </div>
              <div v-if="approval.tool_args" class="approval-item">
                <span class="label">参数：</span>
                <code class="params">{{ JSON.stringify(approval.tool_args, null, 2) }}</code>
              </div>
            </div>
            <div class="approval-actions">
              <button
                class="btn btn-primary btn-small"
                @click="handleApprove(approval.id)"
              >
                ✅ 通过
              </button>
              <button
                class="btn btn-danger btn-small"
                @click="handleReject(approval.id)"
              >
                ❌ 拒绝
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 审核历史 -->
      <div v-if="activeTab === 'history'" class="tab-content">
        <div v-if="approvalStore.isLoading" class="loading-state">
          <div class="loading-dots"><span></span><span></span><span></span></div>
          <span>加载中...</span>
        </div>

        <div v-else-if="approvalStore.approvalHistory.length === 0" class="empty-state">
          <div class="empty-state-icon">📋</div>
          <div class="empty-state-text">暂无审核历史</div>
        </div>

        <div v-else class="history-list">
          <div
            v-for="item in approvalStore.approvalHistory"
            :key="item.id"
            class="history-card"
          >
            <div class="history-header">
              <div class="history-id">#{{ item.id.slice(0, 8) }}</div>
              <span class="tag" :class="item.status === 'approved' ? 'tag-success' : 'tag-danger'">
                {{ item.status === 'approved' ? '已通过' : '已拒绝' }}
              </span>
            </div>
            <div class="history-body">
              <div class="history-item">
                <span class="label">工具：</span>
                <span class="value">{{ item.tool_name }}</span>
              </div>
              <div class="history-item">
                <span class="label">审核时间：</span>
                <span class="value">{{ formatDate(item.resolved_at) }}</span>
              </div>
              <div v-if="item.reason" class="history-item">
                <span class="label">备注：</span>
                <span class="value">{{ item.reason }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 创建审核请求 -->
      <div v-if="activeTab === 'create'" class="tab-content">
        <div class="create-form card">
          <div class="form-group">
            <label class="form-label">工具名称 *</label>
            <select v-model="createForm.tool_name" class="input">
              <option value="">请选择工具</option>
              <option value="web_search">联网搜索</option>
              <option value="file_delete">文件删除</option>
              <option value="database_write">数据库写入</option>
              <option value="file_write">文件写入</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">请求原因 *</label>
            <textarea
              v-model="createForm.reason"
              class="input"
              placeholder="请说明需要使用该工具的原因..."
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="form-label">工具参数（JSON格式）</label>
            <textarea
              v-model="createForm.params"
              class="input"
              placeholder='{"query": "搜索内容"}'
              rows="3"
            ></textarea>
          </div>

          <button
            class="btn btn-primary"
            :disabled="!createForm.tool_name || !createForm.reason || isCreating"
            @click="handleCreate"
          >
            {{ isCreating ? '创建中...' : '创建审核请求' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 审核弹窗 -->
    <div v-if="showRejectModal" class="modal-overlay" @click.self="showRejectModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">拒绝审核</h3>
          <button class="btn-icon" @click="showRejectModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">拒绝原因（可选）</label>
            <textarea
              v-model="rejectComment"
              class="input"
              placeholder="请说明拒绝原因..."
              rows="3"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showRejectModal = false">取消</button>
          <button class="btn btn-danger" @click="confirmReject">确认拒绝</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useApprovalStore } from '../stores/approval'
import { useChatStore } from '../stores/chat'
import * as api from '../api'

const emit = defineEmits(['close'])

const approvalStore = useApprovalStore()
const chatStore = useChatStore()

const activeTab = ref('pending')
const isCreating = ref(false)
const showRejectModal = ref(false)
const rejectComment = ref('')
const currentRejectId = ref(null)

// 工作流 interrupt 待审核状态
const workflowPending = ref(null)

// 总待审核数 = 旧审核系统 + 工作流 interrupt
const totalPendingCount = computed(() => {
  const oldCount = approvalStore.pendingApprovals.length
  const workflowCount = workflowPending.value ? 1 : 0
  return oldCount + workflowCount
})

// 创建表单
const createForm = ref({
  tool_name: '',
  reason: '',
  params: ''
})

// 检查工作流 interrupt 状态
const checkWorkflowInterrupt = async () => {
  try {
    const checkRes = await api.checkApprovalStatus(chatStore.userId)
    const data = checkRes.data.data
    if (data && data.needs_approval) {
      workflowPending.value = {
        tool_info: data.tool_info || '未知工具',
        thread_id: data.thread_id || chatStore.userId
      }
    } else {
      workflowPending.value = null
    }
  } catch (error) {
    // 检查失败不影响
    console.log('工作流 interrupt 检查跳过:', error.message)
  }
}

// 刷新数据（同时检查两套系统）
const refreshData = async () => {
  await Promise.all([
    approvalStore.fetchPendingApprovals(chatStore.userId),
    approvalStore.fetchApprovalHistory(chatStore.userId),
    checkWorkflowInterrupt()
  ])
}

// ========== 工作流 interrupt 的通过/拒绝 ==========

const handleWorkflowApprove = async () => {
  try {
    const resumeRes = await api.resumeAfterApproval(
      chatStore.userId,
      workflowPending.value.thread_id,
      true
    )

    // 将工作流恢复后的回复推送到聊天面板
    const reply = resumeRes.data?.data?.reply
    if (reply) {
      window.dispatchEvent(new CustomEvent('approval-reply', {
        detail: { reply: `✅ 审核已通过，工具执行完成：\n\n${reply}` }
      }))
    }

    // 立即清除 interrupt 状态
    workflowPending.value = null
    
    // 刷新审核历史
    await approvalStore.fetchApprovalHistory(chatStore.userId)
    
    // 检查是否有新的 interrupt（工作流可能继续产生新的审核需求）
    await checkWorkflowInterrupt()
  } catch (error) {
    alert('操作失败: ' + error.message)
  }
}

const handleWorkflowReject = () => {
  currentRejectId.value = '__workflow__'
  rejectComment.value = ''
  showRejectModal.value = true
}

// ========== 旧审核系统的通过/拒绝 ==========

const handleApprove = async (approvalId) => {
  try {
    await approvalStore.submitApprovalResult(chatStore.userId, approvalId, true)
    await approvalStore.fetchPendingApprovals(chatStore.userId)
    await approvalStore.fetchApprovalHistory(chatStore.userId)
  } catch (error) {
    alert('操作失败: ' + error.message)
  }
}

const handleReject = (approvalId) => {
  currentRejectId.value = approvalId
  rejectComment.value = ''
  showRejectModal.value = true
}

// 确认拒绝（区分工作流和旧系统）
const confirmReject = async () => {
  try {
    if (currentRejectId.value === '__workflow__') {
      // 工作流 interrupt 拒绝
      const resumeRes = await api.resumeAfterApproval(
        chatStore.userId,
        workflowPending.value.thread_id,
        false
      )
      const reply = resumeRes.data?.data?.reply
      if (reply) {
        window.dispatchEvent(new CustomEvent('approval-reply', {
          detail: { reply: `❌ 审核已拒绝：\n\n${reply}` }
        }))
      }
      workflowPending.value = null
      await approvalStore.fetchApprovalHistory(chatStore.userId)
      await checkWorkflowInterrupt()
    } else {
      // 旧审核系统拒绝
      await approvalStore.submitApprovalResult(
        chatStore.userId,
        currentRejectId.value,
        false,
        rejectComment.value
      )
    }

    showRejectModal.value = false
  } catch (error) {
    alert('操作失败: ' + error.message)
  }
}

// ========== 创建审核请求 ==========

const handleCreate = async () => {
  isCreating.value = true

  try {
    let params = {}
    if (createForm.value.params.trim()) {
      try {
        params = JSON.parse(createForm.value.params)
      } catch {
        alert('参数格式错误，请输入有效的JSON')
        return
      }
    }

    await approvalStore.createApproval({
      user_id: chatStore.userId,
      tool_name: createForm.value.tool_name,
      tool_args: params,
      reason: createForm.value.reason
    })

    createForm.value = { tool_name: '', reason: '', params: '' }
    activeTab.value = 'pending'
    await refreshData()
    alert('审核请求创建成功！')
  } catch (error) {
    alert('创建失败: ' + error.message)
  } finally {
    isCreating.value = false
  }
}

// ========== 工具函数 ==========

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 监听 ChatPanel 发出的 approval-needed 事件，自动刷新
const onApprovalNeeded = () => {
  activeTab.value = 'pending'
  checkWorkflowInterrupt()
}

onMounted(() => {
  refreshData()
  window.addEventListener('approval-needed', onApprovalNeeded)
})

onUnmounted(() => {
  window.removeEventListener('approval-needed', onApprovalNeeded)
})
</script>

<style scoped>
.approval-panel {
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

.pending-count {
  background-color: var(--warning-color);
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 内容 */
.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

/* 标签页 */
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background-color: var(--bg-input);
  padding: 4px;
  border-radius: 8px;
}

.tab {
  flex: 1;
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  background-color: var(--primary-color);
  color: white;
}

.tab-badge {
  background-color: var(--danger-color);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.tab-content {
  min-height: 300px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: var(--text-muted);
}

/* 审核卡片 */
.approval-list, .history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.approval-card, .history-card {
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}

/* 工作流 interrupt 卡片高亮 */
.workflow-interrupt-card {
  border-color: var(--warning-color);
  border-width: 2px;
  background: linear-gradient(135deg, var(--bg-input) 0%, rgba(255, 193, 7, 0.05) 100%);
}

.approval-header, .history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.approval-id, .history-id {
  font-family: monospace;
  font-size: 14px;
  color: var(--text-muted);
}

.approval-body, .history-body {
  margin-bottom: 16px;
}

.approval-item, .history-item {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;
}

.approval-item .label, .history-item .label {
  color: var(--text-muted);
  width: 80px;
  flex-shrink: 0;
}

.approval-item .value, .history-item .value {
  color: var(--text-primary);
}

.params {
  display: block;
  background-color: var(--bg-dark);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.approval-actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

/* 创建表单 */
.create-form {
  max-width: 500px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: var(--text-muted);
}

.empty-state-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state-text {
  font-size: 16px;
}
</style>
