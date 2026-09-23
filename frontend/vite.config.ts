import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command, mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }
  if (command === 'build' && env.VITE_USE_MOCK_API === 'true') {
    throw new Error('VITE_USE_MOCK_API=true is development-only; production must use the backend.')
  }
  return {
    plugins: [react()],
    server: { proxy: { '/api': 'http://localhost:8000' } },
  }
})
