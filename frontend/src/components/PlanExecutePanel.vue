<template>
  <div class="plan-execute-panel">
    <!-- 头部：任务信息和进度 -->
    <div class="panel-header" v-if="planExecuteStore.currentTask">
      <div class="task-info">
        <span class="label">当前任务:</span>
        <span class="task-text">{{ planExecuteStore.currentTask }}</span>
      </div>
      
      <!-- 进度条 -->
      <div class="progress-section" v-if="planExecuteStore.isExecuting || planExecuteStore.isComplete">
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: planExecuteStore.progressPercent + '%' }"
            :class="{ 'complete': planExecuteStore.isComplete }"
          ></div>
        </div>
        <div class="progress-text">
          {{ planExecuteStore.completedSteps }} / {{ planExecuteStore.totalSteps }} 步骤
          <span v-if="planExecuteStore.replanCount > 0" class="replan-badge">
            重规划 {{ planExecuteStore.replanCount }} 次
          </span>
        </div>
      </div>
    </div>

    <!-- 执行计划 -->
    <div class="plan-section" v-if="planExecuteStore.plan.length > 0">
      <h4 class="section-title">
        <span class="icon">📋</span>
        执行计划
      </h4>
      <div class="plan-steps">
        <div 
          v-for="(step, index) in planExecuteStore.plan" 
          :key="index"
          class="plan-step"
          :class="{
            'completed': index < planExecuteStore.currentStepIndex,
            'current': index === planExecuteStore.currentStepIndex && planExecuteStore.isExecuting,
            'pending': index > planExecuteStore.currentStepIndex
          }"
        >
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-content">
            <div class="step-text">{{ step }}</div>
            <!-- 步骤结果 -->
            <div 
              v-if="getStepResult(index)" 
              class="step-result"
              :class="{ 'success': getStepResult(index).success, 'error': !getStepResult(index).success }"
            >
              <div class="result-header">
                <span class="tool-badge">{{ getStepResult(index).tool_used }}</span>
                <span class="status-icon">{{ getStepResult(index).success ? '✓' : '✗' }}</span>
              </div>
              <div class="result-text">{{ getStepResult(index).result }}</div>
            </div>
          </div>
          <div class="step-status">
            <span v-if="index < planExecuteStore.currentStepIndex" class="status completed">✓</span>
            <span v-else-if="index === planExecuteStore.currentStepIndex && planExecuteStore.isExecuting" class="status loading">
              <span class="spinner"></span>
            </span>
            <span v-else class="status pending">○</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 执行中提示 -->
    <div class="executing-hint" v-if="planExecuteStore.isExecuting && planExecuteStore.plan.length === 0">
      <span class="spinner"></span>
      <span>正在生成执行计划...</span>
    </div>

    <!-- 最终回答 -->
    <div class="final-response" v-if="planExecuteStore.finalResponse">
      <h4 class="section-title">
        <span class="icon">📝</span>
        最终回答
      </h4>
      <div class="response-content">{{ planExecuteStore.finalResponse }}</div>
    </div>

    <!-- 错误信息 -->
    <div class="error-message" v-if="planExecuteStore.error">
      <span class="icon">❌</span>
      {{ planExecuteStore.error }}
    </div>

    <!-- 操作按钮 -->
    <div class="panel-actions" v-if="!planExecuteStore.isExecuting">
      <button 
        v-if="planExecuteStore.isComplete || planExecuteStore.error"
        class="btn btn-primary"
        @click="handleNewTask"
      >
        新任务
      </button>
      <button 
        v-if="planExecuteStore.stepResults.length > 0"
        class="btn btn-secondary"
        @click="handleClear"
      >
        清除
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePlanExecuteStore } from '../stores/planExecute.js'

const planExecuteStore = usePlanExecuteStore()

// 获取指定索引的步骤结果
const getStepResult = (index) => {
  return planExecuteStore.stepResults[index] || null
}

// 开始新任务
const handleNewTask = () => {
  planExecuteStore.reset()
}

// 清除结果
const handleClear = () => {
  planExecuteStore.reset()
}
</script>

<style scoped>
.plan-execute-panel {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #e9ecef;
}

/* 头部 */
.panel-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #dee2e6;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.task-info .label {
  font-weight: 600;
  color: #495057;
  font-size: 14px;
}

.task-info .task-text {
  color: #212529;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 进度条 */
.progress-section {
  margin-top: 8px;
}

.progress-bar {
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff, #0056b3);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-fill.complete {
  background: linear-gradient(90deg, #28a745, #1e7e34);
}

.progress-text {
  font-size: 12px;
  color: #6c757d;
  display: flex;
  align-items: center;
  gap: 8px;
}

.replan-badge {
  background: #ffc107;
  color: #212529;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
}

/* 计划步骤 */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #495057;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-title .icon {
  font-size: 16px;
}

.plan-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  transition: all 0.2s ease;
}

.plan-step.completed {
  border-color: #28a745;
  background: #f8fff9;
}

.plan-step.current {
  border-color: #007bff;
  background: #f0f8ff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
}

.plan-step.pending {
  opacity: 0.7;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e9ecef;
  color: #495057;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.plan-step.completed .step-number {
  background: #28a745;
  color: white;
}

.plan-step.current .step-number {
  background: #007bff;
  color: white;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-text {
  font-size: 14px;
  color: #212529;
  line-height: 1.5;
}

/* 步骤结果 */
.step-result {
  margin-top: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #6c757d;
}

.step-result.success {
  border-left-color: #28a745;
  background: #f8fff9;
}

.step-result.error {
  border-left-color: #dc3545;
  background: #fff8f8;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.tool-badge {
  font-size: 11px;
  background: #e9ecef;
  color: #495057;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-icon {
  font-size: 12px;
  font-weight: bold;
}

.step-result.success .status-icon {
  color: #28a745;
}

.step-result.error .status-icon {
  color: #dc3545;
}

.result-text {
  font-size: 12px;
  color: #6c757d;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.step-status {
  flex-shrink: 0;
}

.step-status .status {
  font-size: 18px;
}

.step-status .status.completed {
  color: #28a745;
}

.step-status .status.pending {
  color: #adb5bd;
}

/* 执行中提示 */
.executing-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  color: #6c757d;
  font-size: 14px;
}

/* 最终回答 */
.final-response {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #dee2e6;
}

.response-content {
  background: white;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  font-size: 14px;
  line-height: 1.6;
  color: #212529;
  white-space: pre-wrap;
}

/* 错误信息 */
.error-message {
  margin-top: 16px;
  padding: 12px;
  background: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 6px;
  color: #c53030;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 操作按钮 */
.panel-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #545b62;
}

/* 加载动画 */
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #e9ecef;
  border-top-color: #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
