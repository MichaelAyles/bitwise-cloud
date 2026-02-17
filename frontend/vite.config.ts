import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    __GIT_SHA__: JSON.stringify(process.env.VITE_GIT_SHA || 'dev'),
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/mcp': 'http://localhost:8000',
    },
  },
})
