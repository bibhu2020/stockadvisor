import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  // Load .env from project root (one level up from ui/)
  envDir: path.resolve(__dirname, '..'),
  plugins: [
    vue(),
    vueDevTools(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'favicon.ico', 'apple-touch-icon.png', 'pwa-192x192.png', 'pwa-512x512.png', 'pwa-512x512-maskable.png'],
      manifest: {
        name: 'AlphaForge',
        short_name: 'AlphaForge',
        description: 'AI-Powered autonomous paper trading intelligence',
        theme_color: '#1e40af',
        background_color: '#1e40af',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: 'favicon.svg',              sizes: 'any',     type: 'image/svg+xml', purpose: 'any' },
          { src: 'pwa-192x192.png',          sizes: '192x192', type: 'image/png',     purpose: 'any' },
          { src: 'pwa-512x512.png',          sizes: '512x512', type: 'image/png',     purpose: 'any' },
          { src: 'pwa-512x512-maskable.png', sizes: '512x512', type: 'image/png',     purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^.*\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
