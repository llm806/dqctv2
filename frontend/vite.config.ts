// frontend/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 配置代理以解决开发过程中的跨域问题
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // 你的FastAPI后端地址
        changeOrigin: true,
      },
    },
  },
})