import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // 状态
  const status = ref({
    doc_count: 0,
    vector_db: 'ChromaDB',
    graph_db: 'Neo4j',
    last_update: null
  })
  const isLoading = ref(false)
  const lastMessage = ref('')
  
  // 获取知识库状态
  const fetchStatus = async () => {
    try {
      const response = await api.getKnowledgeStatus()
      if (response.data.code === 200) {
        status.value = response.data.data
      }
    } catch (error) {
      console.error('获取知识库状态失败:', error)
    }
  }
  
  // 增量更新知识库
  const updateIncremental = async (userId) => {
    isLoading.value = true
    try {
      const response = await api.updateKnowledge(userId, true)
      if (response.data.code === 200) {
        lastMessage.value = response.data.message || '增量更新完成'
      } else {
        lastMessage.value = response.data.message || '更新失败'
      }
      await fetchStatus()
      return response.data
    } catch (error) {
      lastMessage.value = `更新失败: ${error.message}`
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  // 全量重建知识库
  const updateFull = async (userId) => {
    isLoading.value = true
    try {
      const response = await api.updateKnowledge(userId, false)
      if (response.data.code === 200) {
        lastMessage.value = response.data.message || '全量重建完成'
      } else {
        lastMessage.value = response.data.message || '重建失败'
      }
      await fetchStatus()
      return response.data
    } catch (error) {
      lastMessage.value = `重建失败: ${error.message}`
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  // 构建知识图谱
  const buildGraph = async () => {
    isLoading.value = true
    try {
      const response = await api.buildKnowledgeGraph()
      lastMessage.value = response.data.message || '图谱构建完成'
      return response.data
    } catch (error) {
      lastMessage.value = `构建失败: ${error.message}`
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // 清空知识图谱
  const clearGraph = async () => {
    isLoading.value = true
    try {
      const response = await api.clearKnowledgeGraph()
      if (response.data.code === 200) {
        lastMessage.value = response.data.message || '图谱已清空'
      } else {
        lastMessage.value = response.data.message || '清空失败'
      }
      return response.data
    } catch (error) {
      lastMessage.value = `清空失败: ${error.message}`
      throw error
    } finally {
      isLoading.value = false
    }
  }

  return {
    status,
    isLoading,
    lastMessage,
    fetchStatus,
    updateIncremental,
    updateFull,
    buildGraph,
    clearGraph
  }
})
