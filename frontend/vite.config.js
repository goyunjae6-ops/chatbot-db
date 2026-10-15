import react from '@vitejs/plugin-react'
import process from 'node:process'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = process.env.VITE_API_URL || env.VITE_API_URL
  if (command === 'build' && mode === 'production') {
    if (!apiUrl || !/^https:\/\//.test(apiUrl) || /localhost|127\.0\.0\.1/.test(apiUrl)) {
      throw new Error('Set VITE_API_URL to the deployed HTTPS backend URL before building.')
    }
  }
  return {
  server: {
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '') } },
  },
  plugins: [
    react({
      babel: {
        plugins: [['babel-plugin-react-compiler', { target: '19' }]],
      },
    }),
  ],
  }
})
