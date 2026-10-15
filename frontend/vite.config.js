import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  server: {
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '') } },
  },
  plugins: [
    react({
      babel: {
        server: {
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '') } },
  },
  plugins: [['babel-plugin-react-compiler', { target: '19' }]],
      },
    }),
  ],
})
