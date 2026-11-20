<script setup lang="ts">
const route = useRoute()
const router = useRouter()


const login = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

const isValid = computed(() => login.value.trim().length > 0 && password.value.length > 0)

async function submit() {
  if (!isValid.value || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    await $fetch('/api/auth/login', {
      method: 'POST',
      body: { login: login.value.trim(), password: password.value },
    })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string }; message?: string }
    error.value = err.data?.detail || 'Неверный логин или пароль'
    password.value = ''
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-100 px-6">
    <form class="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-8 shadow-sm" @submit.prevent="submit">
      <h1 class="mb-1 text-xl font-semibold">Keitaro Manager</h1>
      <p class="mb-6 text-sm text-slate-500">Вход в панель управления</p>

      <div class="mb-4">
        <label class="mb-1 block text-sm font-medium">Логин</label>
        <input
          v-model="login"
          type="text"
          autocomplete="username"
          autofocus
          class="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        >
      </div>

      <div class="mb-4">
        <label class="mb-1 block text-sm font-medium">Пароль</label>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          class="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        >
      </div>

      <p v-if="error" class="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

      <button
        type="submit"
        class="w-full rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        :disabled="!isValid || submitting"
      >
        {{ submitting ? 'Вход…' : 'Войти' }}
      </button>
    </form>
  </div>
</template>
