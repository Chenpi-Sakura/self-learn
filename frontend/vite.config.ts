import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,  // 沿用 5174
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // spec § 10.2: 关闭 proxy buffering 避免 SSE 流式变批量
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['cache-control'] = 'no-cache';
          });
        },
      },
    },
  },
});