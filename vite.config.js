import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The integrated session service/gateway runs on loopback 8021.
// Development and preview use the same origin and never default to protected ports.
const API_TARGET = process.env.REVELIO_API_URL || 'http://127.0.0.1:8021'
const proxy = {
  '/api': { target: API_TARGET, changeOrigin: false },
  '/wt-api': { target: process.env.REVELIO_GATEWAY_URL || 'http://127.0.0.1:8021', changeOrigin: false },
}

export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5182, proxy },
  preview: { host: '127.0.0.1', port: 5182, proxy },
})
