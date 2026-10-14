import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

const srcDir = fileURLToPath(new URL('./src', import.meta.url));
const bkuiDist = fileURLToPath(
  new URL('./node_modules/bkui-vue/dist/index.esm.js', import.meta.url),
);

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: [
      { find: '@', replacement: srcDir },
      { find: /^bkui-vue$/, replacement: bkuiDist },
    ],
  },
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
    cors: true,
    watch: {
      usePolling: true,
    },
  },
});
