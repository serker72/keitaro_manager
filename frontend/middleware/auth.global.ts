/** Глобальная проверка сессии: нет валидной cookie — редирект на /login. */
export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/login') return

  // useRequestFetch пробрасывает cookie при SSR, на клиенте работает как $fetch
  const requestFetch = useRequestFetch()
  try {
    await requestFetch('/api/auth/me')
  } catch {
    return navigateTo({ path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} })
  }
})
