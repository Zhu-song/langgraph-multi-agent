import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api'

export const useApprovalStore = defineStore('approval', () => {
  // 状态
  const pendingApprovals = ref([])
  const approvalHistory = ref([])
  const isLoading = ref(false)
  const currentApproval = ref(null)
  
  // 获取待审核列表
  const fetchPendingApprovals = async (userId) => {
    isLoading.value = true
    try {
      const response = await api.getPendingApprovals(userId)
      if (response.data.code === 200) {
        pendingApprovals.value = response.data.data.approvals
      }
    } catch (error) {
      console.error('获取待审核列表失败:', error)
    } finally {
      isLoading.value = false
    }
  }
  
  // 获取审核历史
  const fetchApprovalHistory = async (userId, limit = 50) => {
    isLoading.value = true
    try {
      const response = await api.getApprovalHistory(userId, limit)
      if (response.data.code === 200) {
        approvalHistory.value = response.data.data.history
      }
    } catch (error) {
      console.error('获取审核历史失败:', error)
    } finally {
      isLoading.value = false
    }
  }
  
  // 创建审核请求
  const createApproval = async (approvalData) => {
    try {
      const response = await api.createApprovalRequest(approvalData)
      return response.data
    } catch (error) {
      console.error('创建审核请求失败:', error)
      throw error
    }
  }
  
  // 提交审核结果
  const submitApprovalResult = async (userId, approvalId, approved, comment = '') => {
    try {
      const response = await api.submitApproval(userId, approvalId, approved, comment)
      // 刷新列表
      await fetchPendingApprovals(userId)
      return response.data
    } catch (error) {
      console.error('提交审核结果失败:', error)
      throw error
    }
  }
  
  // 获取审核详情
  const fetchApprovalDetail = async (userId, approvalId) => {
    try {
      const response = await api.getApprovalDetail(userId, approvalId)
      if (response.data.code === 200) {
        currentApproval.value = response.data.data
      }
      return currentApproval.value
    } catch (error) {
      console.error('获取审核详情失败:', error)
      throw error
    }
  }
  
  // 清理超时审核
  const cleanupTimeouts = async () => {
    try {
      const response = await api.cleanupTimeoutApprovals()
      return response.data
    } catch (error) {
      console.error('清理超时审核失败:', error)
      throw error
    }
  }
  
  return {
    pendingApprovals,
    approvalHistory,
    isLoading,
    currentApproval,
    fetchPendingApprovals,
    fetchApprovalHistory,
    createApproval,
    submitApprovalResult,
    fetchApprovalDetail,
    cleanupTimeouts
  }
})
