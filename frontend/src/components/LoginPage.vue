<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <span class="login-logo">🤖</span>
        <h1>LangGraph Agent</h1>
        <p>多智能体对话助手</p>
      </div>

      <!-- 标签切换 -->
      <div class="login-tabs">
        <button
          class="login-tab"
          :class="{ active: mode === 'login' }"
          @click="mode = 'login'"
        >登录</button>
        <button
          class="login-tab"
          :class="{ active: mode === 'register' }"
          @click="mode = 'register'"
        >注册</button>
      </div>

      <!-- 登录表单 -->
      <div v-if="mode === 'login'" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="loginForm.name"
            class="input"
            placeholder="请输入用户名"
            @keydown.enter="handleLogin"
            ref="loginNameInput"
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <div class="input-with-toggle">
            <input
              v-model="loginForm.password"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="请输入密码"
              @keydown.enter="handleLogin"
            />
            <span class="toggle-pwd" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁' }}
            </span>
          </div>
        </div>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <button class="btn-login" :disabled="isSubmitting" @click="handleLogin">
          {{ isSubmitting ? '登录中...' : '登 录' }}
        </button>
        <div class="forgot-link" @click="mode = 'forgot'">忘记密码？</div>
      </div>

      <!-- 注册表单 -->
      <div v-if="mode === 'register'" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="registerForm.name"
            class="input"
            placeholder="请输入用户名"
            @keydown.enter="handleRegister"
            ref="registerNameInput"
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <div class="input-with-toggle">
            <input
              v-model="registerForm.password"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="至少6位密码"
              @keydown.enter="handleRegister"
            />
            <span class="toggle-pwd" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁' }}
            </span>
          </div>
        </div>
        <div class="form-group">
          <label>确认密码</label>
          <div class="input-with-toggle">
            <input
              v-model="registerForm.confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="再次输入密码"
              @keydown.enter="handleRegister"
            />
            <span class="toggle-pwd" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁' }}
            </span>
          </div>
        </div>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <button class="btn-login" :disabled="isSubmitting" @click="handleRegister">
          {{ isSubmitting ? '注册中...' : '注 册' }}
        </button>
      </div>

      <!-- 忘记密码表单 -->
      <div v-if="mode === 'forgot'" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="forgotForm.name"
            class="input"
            placeholder="请输入用户名"
            @keydown.enter="handleForgot"
            ref="forgotNameInput"
          />
        </div>
        <div class="form-group">
          <label>新密码</label>
          <div class="input-with-toggle">
            <input
              v-model="forgotForm.newPassword"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="至少6位新密码"
              @keydown.enter="handleForgot"
            />
            <span class="toggle-pwd" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁' }}
            </span>
          </div>
        </div>
        <div class="form-group">
          <label>确认新密码</label>
          <div class="input-with-toggle">
            <input
              v-model="forgotForm.confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="再次输入新密码"
              @keydown.enter="handleForgot"
            />
            <span class="toggle-pwd" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁' }}
            </span>
          </div>
        </div>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <div v-if="successMsg" class="success-msg">{{ successMsg }}</div>
        <button class="btn-login" :disabled="isSubmitting" @click="handleForgot">
          {{ isSubmitting ? '重置中...' : '重置密码' }}
        </button>
        <div class="forgot-link" @click="mode = 'login'; errorMsg = ''; successMsg = ''">返回登录</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '../api'

const emit = defineEmits(['login-success'])

const mode = ref('login')
const isSubmitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const showPassword = ref(false)

const loginForm = ref({ name: '', password: '' })
const registerForm = ref({ name: '', password: '', confirmPassword: '' })
const forgotForm = ref({ name: '', newPassword: '', confirmPassword: '' })

const loginNameInput = ref(null)
const registerNameInput = ref(null)
const forgotNameInput = ref(null)

const handleLogin = async () => {
  errorMsg.value = ''
  
  if (!loginForm.value.name.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!loginForm.value.password) {
    errorMsg.value = '请输入密码'
    return
  }

  isSubmitting.value = true
  try {
    const res = await api.authLogin(loginForm.value.name, loginForm.value.password)
    if (res.data.code === 200) {
      emit('login-success', res.data.data)
    } else {
      errorMsg.value = res.data.message
    }
  } catch (error) {
    errorMsg.value = '登录失败，请检查网络'
  } finally {
    isSubmitting.value = false
  }
}

const handleRegister = async () => {
  errorMsg.value = ''

  if (!registerForm.value.name.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (registerForm.value.password.length < 6) {
    errorMsg.value = '密码至少6位'
    return
  }
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    errorMsg.value = '两次密码不一致'
    return
  }

  isSubmitting.value = true
  try {
    const res = await api.authRegister(registerForm.value.name, registerForm.value.password)
    if (res.data.code === 200) {
      // 注册成功，自动登录
      emit('login-success', res.data.data)
    } else {
      errorMsg.value = res.data.message
    }
  } catch (error) {
    errorMsg.value = '注册失败，请检查网络'
  } finally {
    isSubmitting.value = false
  }
}

const handleForgot = async () => {
  errorMsg.value = ''
  successMsg.value = ''

  if (!forgotForm.value.name.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (forgotForm.value.newPassword.length < 6) {
    errorMsg.value = '新密码至少6位'
    return
  }
  if (forgotForm.value.newPassword !== forgotForm.value.confirmPassword) {
    errorMsg.value = '两次密码不一致'
    return
  }

  isSubmitting.value = true
  try {
    const res = await api.resetPassword(forgotForm.value.name, forgotForm.value.newPassword)
    if (res.data.code === 200) {
      successMsg.value = '密码重置成功！请返回登录'
      errorMsg.value = ''
    } else {
      errorMsg.value = res.data.message
    }
  } catch (error) {
    errorMsg.value = '重置失败，请检查网络'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  loginNameInput.value?.focus()
})
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
}

.login-card {
  width: 400px;
  background-color: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: white;
  margin-bottom: 4px;
}

.login-header p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

/* 标签切换 */
.login-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 28px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 4px;
}

.login-tab {
  flex: 1;
  padding: 10px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.login-tab.active {
  background-color: #2dd4bf;
  color: #1a1a2e;
}

.login-tab:hover:not(.active) {
  color: white;
}

/* 表单 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
}

.input {
  padding: 12px 16px;
  background-color: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  color: white;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.input-with-toggle {
  position: relative;
}

.input-with-toggle .input {
  padding-right: 42px;
}

.toggle-pwd {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  font-size: 16px;
  user-select: none;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.toggle-pwd:hover {
  opacity: 1;
}

.input:focus {
  border-color: #2dd4bf;
  background-color: rgba(255, 255, 255, 0.1);
}

.error-msg {
  padding: 10px 14px;
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 13px;
}

.btn-login {
  padding: 14px;
  background-color: #2dd4bf;
  border: none;
  border-radius: 10px;
  color: #1a1a2e;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 4px;
}

.btn-login:hover:not(:disabled) {
  background-color: #14b8a6;
  transform: translateY(-1px);
}

.btn-login:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.forgot-link {
  text-align: center;
  margin-top: 16px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s ease;
}
.forgot-link:hover {
  color: #2dd4bf;
}

.success-msg {
  padding: 10px 14px;
  background-color: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  color: #86efac;
  font-size: 13px;
}
</style>
