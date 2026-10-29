import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  resolve: {
    alias: {
      // Resolve @craftlife/core to the package SOURCE, mirroring the tsconfig
      // `paths` mapping. This keeps `npx vite build` standalone — no requirement
      // to build packages/craftlife-core/dist first (UPDATE_RULES §7 gate).
      // External consumers (the sibling CraftLife-Android project) use the
      // compiled dist/ via the package.json `exports` map instead.
      '@craftlife/core': fileURLToPath(
        new URL('../packages/craftlife-core/src/index.ts', import.meta.url),
      ),
    },
  },
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
