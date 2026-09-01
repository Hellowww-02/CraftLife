import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets',
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
      // Streamfile audio lokal (music/stream, reminder sound) juga dipakai
      // sebagai src <audio> relative; dev server harus meneruskannya ke API
      // 8765, bukan mengembalikan SPA fallback (memutus pemutaran MP3).
      '/music': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
});
