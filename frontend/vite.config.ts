import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: Object.fromEntries(
      ['/api', '/guia', '/guide.css'].map((path) => [path, 'http://127.0.0.1:8000']),
    ),
  },
})
