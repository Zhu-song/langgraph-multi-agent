import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { planExecute, planExecuteStream, getPlanExecuteStatus } from '../api/index.js'

/**
 * Plan and Execute 状态管理
 * 
 * 管理 Plan-Execute 任务的执行状态、进度和结果
 */
export const usePlanExecuteStore = defineStore('planExecute', () => {
  // ==================== State ====================
  
  // 当前任务状态
  const isExecuting = ref(false)
  const currentTask = ref('')
  
  // 执行计划
  const plan = ref([])
  const currentStepIndex = ref(0)
  
  // 步骤结果
  const stepResults = ref([])
  
  // 最终回答
  const finalResponse = ref('')
  
  // 重规划次数
  const replanCount = ref(0)
  
  // 错误信息
  const error = ref(null)
  
  // 执行模式: 'sync' | 'stream'
  const executionMode = ref('stream')
  
  // ==================== Getters ====================
  
  // 是否已完成
  const isComplete = computed(() => {
    return finalResponse.value !== '' && !isExecuting.value
  })
  
  // 当前步骤
  const currentStep = computed(() => {
    if (plan.value.length === 0) return null
    if (currentStepIndex.value >= plan.value.length) return null
    return plan.value[currentStepIndex.value]
  })
  
  // 进度百分比
  const progressPercent = computed(() => {
    if (plan.value.length === 0) return 0
    return Math.round((currentStepIndex.value / plan.value.length) * 100)
  })
  
  // 已完成的步骤数
  const completedSteps = computed(() => {
    return stepResults.value.length
  })
  
  // 总步骤数
  const totalSteps = computed(() => {
    return plan.value.length
  })
  
  // 是否可以开始新任务
  const canStartNew = computed(() => {
    return !isExecuting.value
  })
  
  // ==================== Actions ====================
  
  /**
   * 重置状态
   */
  const reset = () => {
    isExecuting.value = false
    currentTask.value = ''
    plan.value = []
    currentStepIndex.value = 0
    stepResults.value = []
    finalResponse.value = ''
    replanCount.value = 0
    error.value = null
  }
  
  /**
   * 同步执行 Plan-Execute
   * @param {string} userId - 用户ID
   * @param {string} query - 任务描述
   */
  const executeSync = async (userId, query) => {
    reset()
    isExecuting.value = true
    currentTask.value = query
    error.value = null
    
    try {
      const response = await planExecute(userId, query)
      
      if (response.data.code === 200) {
        const data = response.data.data
        plan.value = data.plan || []
        stepResults.value = data.step_results || []
        finalResponse.value = data.final_response || ''
        replanCount.value = data.replan_count || 0
        currentStepIndex.value = stepResults.value.length
      } else {
        error.value = response.data.message || '执行失败'
      }
    } catch (err) {
      error.value = err.message || '网络错误'
      console.error('Plan-Execute 同步执行失败:', err)
    } finally {
      isExecuting.value = false
    }
  }
  
  /**
   * 流式执行 Plan-Execute
   * @param {string} userId - 用户ID
   * @param {string} query - 任务描述
   * @param {Function} onEvent - 事件回调函数
   */
  const executeStream = async (userId, query, onEvent = null) => {
    reset()
    isExecuting.value = true
    currentTask.value = query
    error.value = null
    
    try {
      const eventStream = planExecuteStream(userId, query)
      
      for await (const event of eventStream) {
        const { type, data } = event
        
        switch (type) {
          case 'start':
            // 任务开始
            if (onEvent) onEvent('start', data)
            break
            
          case 'plan_generated':
            // 计划生成完成
            plan.value = data.plan || []
            if (onEvent) onEvent('plan_generated', data)
            break
            
          case 'step_completed':
            // 步骤完成
            stepResults.value.push({
              step: data.step,
              result: data.result,
              tool_used: data.tool_used,
              success: data.success
            })
            currentStepIndex.value = data.step_index
            if (onEvent) onEvent('step_completed', data)
            break
            
          case 'plan_adjusted':
            // 计划调整
            plan.value = data.new_plan || []
            replanCount.value = data.replan_count || 0
            if (onEvent) onEvent('plan_adjusted', data)
            break
            
          case 'final_response':
            // 最终回答
            finalResponse.value = data.response || ''
            if (onEvent) onEvent('final_response', data)
            break
            
          case 'error':
            // 错误
            error.value = data.error || '执行错误'
            if (onEvent) onEvent('error', data)
            break
            
          case 'done':
            // 完成
            if (onEvent) onEvent('done', data)
            break
            
          default:
            if (onEvent) onEvent(type, data)
        }
      }
    } catch (err) {
      error.value = err.message || '流式执行失败'
      console.error('Plan-Execute 流式执行失败:', err)
    } finally {
      isExecuting.value = false
    }
  }
  
  /**
   * 执行 Plan-Execute（根据当前模式自动选择）
   * @param {string} userId - 用户ID
   * @param {string} query - 任务描述
   * @param {Function} onEvent - 流式事件回调（仅在流式模式下使用）
   */
  const execute = async (userId, query, onEvent = null) => {
    if (executionMode.value === 'stream') {
      return executeStream(userId, query, onEvent)
    } else {
      return executeSync(userId, query)
    }
  }
  
  /**
   * 查询执行状态
   * @param {string} userId - 用户ID
   */
  const fetchStatus = async (userId) => {
    try {
      const response = await getPlanExecuteStatus(userId)
      return response.data
    } catch (err) {
      console.error('获取 Plan-Execute 状态失败:', err)
      return null
    }
  }
  
  /**
   * 设置执行模式
   * @param {string} mode - 'sync' 或 'stream'
   */
  const setExecutionMode = (mode) => {
    executionMode.value = mode
  }
  
  return {
    // State
    isExecuting,
    currentTask,
    plan,
    currentStepIndex,
    stepResults,
    finalResponse,
    replanCount,
    error,
    executionMode,
    
    // Getters
    isComplete,
    currentStep,
    progressPercent,
    completedSteps,
    totalSteps,
    canStartNew,
    
    // Actions
    reset,
    executeSync,
    executeStream,
    execute,
    fetchStatus,
    setExecutionMode
  }
})
