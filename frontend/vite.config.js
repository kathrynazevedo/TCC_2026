import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from "node:url"

// Em desenvolvimento o front chama "/api" e o Vite repassa ao backend (sem CORS, funciona também pela rede local).
const backend = process.env.VITE_PROXY_TARGET || 'http://localhost:3000'
const proxy = { '/api': { target: backend, changeOrigin: true } }

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
  build: {
    rollupOptions: {
      output: {
        // Bibliotecas pesadas e estáveis em arquivos próprios: melhor cache e carregamento por página.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/node_modules\/(recharts|d3-[^/]+|victory-vendor)\//.test(id)) return 'charts'
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) return 'react'
          return undefined
        },
      },
    },
  },
})
