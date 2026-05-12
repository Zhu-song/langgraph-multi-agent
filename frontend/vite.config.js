import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/rag': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/knowledge': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/plan-execute': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
