import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' 让产物用相对路径引用资源，这样无论部署在根路径还是
// 被 VitePress 以 /demo/ 子路径嵌入（iframe），资源都能正确加载。
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    // 允许导入 src/samples 下的 JSON
    assetsInlineLimit: 0,
  },
  server: {
    // 本地开发时把 /api 代理到本地 FastAPI 服务（server.py），实现"在线运行"联调
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
