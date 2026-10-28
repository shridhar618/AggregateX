import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The local FastAPI engine runs on 127.0.0.1:8000. The dev and preview servers
// proxy /api to it so the browser only ever talks to one local origin.
const API_TARGET = process.env.REVELIO_API_URL || 'http://127.0.0.1:8000'
const proxy = { '/api': { target: API_TARGET, changeOrigin: false } }

export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, proxy },
  preview: { host: '127.0.0.1', port: 4173, proxy },
})
