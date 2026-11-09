// web/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // Le navigateur appelle /api/... sur le serveur Vite (5173), qui relaie vers FastAPI (8000).
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (chemin) => chemin.replace(/^\/api/, ''),
      },
    },
  },
})