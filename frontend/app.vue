<template>
  <div class="min-h-screen bg-slate-100 text-slate-900">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <NuxtLink to="/" class="text-lg font-semibold tracking-tight">Keitaro Manager</NuxtLink>
        <nav class="flex gap-4 text-sm">
          <NuxtLink to="/" class="text-slate-600 hover:text-slate-900">Кампании</NuxtLink>
          <NuxtLink to="/campaigns/new" class="rounded bg-slate-900 px-3 py-1.5 text-white hover:bg-slate-700">
            Создать кампанию
          </NuxtLink>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-6 py-8">
      <NuxtPage />
    </main>
  </div>
</template>
