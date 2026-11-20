// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  modules: ['@nuxtjs/tailwindcss', '@nuxt/eslint'],

  // Проксируем /api/** на бэкенд, чтобы не зависеть от CORS
  routeRules: {
    '/api/**': {
      proxy: `${process.env.NUXT_BACKEND_URL || 'http://localhost:33000'}/api/**`,
    },
  },

  runtimeConfig: {
    public: {
      // Ссылка VIEW IN KT (админка Keitaro)
      keitaroAdminUrl: process.env.KEITARO_BASE_URL || 'https://tlgk.host/admin',
    },
  },

  app: {
    head: {
      title: 'Keitaro Manager',
    },
  },
})
