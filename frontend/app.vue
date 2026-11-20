<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const isLoginPage = computed(() => route.path === '/login')
const loggingOut = ref(false)

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await $fetch('/api/auth/logout', { method: 'POST' })
  } finally {
    loggingOut.value = false
    await router.push('/login')
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-100 text-slate-900">
    <header v-if="!isLoginPage" class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <NuxtLink to="/" class="text-lg font-semibold tracking-tight">Keitaro Manager</NuxtLink>
        <nav class="flex items-center gap-4 text-sm">
          <NuxtLink to="/" class="text-slate-600 hover:text-slate-900">Кампании</NuxtLink>
          <NuxtLink to="/campaigns/new" class="rounded bg-slate-900 px-3 py-1.5 text-white hover:bg-slate-700">
            Создать кампанию
          </NuxtLink>
          <button
            class="rounded border border-slate-300 px-3 py-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            :disabled="loggingOut"
            @click="logout"
          >
            {{ loggingOut ? 'Выход…' : 'Logout' }}
          </button>
        </nav>
      </div>
    </header>
    <main :class="isLoginPage ? '' : 'mx-auto max-w-6xl px-6 py-8'">
      <NuxtPage />
    </main>
  </div>
</template>
