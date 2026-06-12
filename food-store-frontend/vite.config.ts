import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy de /api/* hacia el backend FastAPI (localhost:8000).
    // `ws: true` es CLAVE para que el upgrade de WebSocket
    // pase a través de Vite y llegue al endpoint /ws/pedidos.
    // En desarrollo, el cliente conecta a ws://localhost:5173/api/ws/pedidos
    // y Vite lo tunelea a ws://localhost:8000/api/ws/pedidos.
    proxy: {
      '/api': {
        target:   'http://localhost:8000',
        ws:       true,
        changeOrigin: true,
      },
    },
  },
})
