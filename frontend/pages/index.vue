<script setup lang="ts">
const api = useApi()
const { data: campaigns, pending, error, refresh } = await useAsyncData('campaigns', () => api.listCampaigns())
</script>

<template>
  <section>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Кампании</h1>
      <button
        class="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
        :disabled="pending"
        @click="refresh()"
      >
        Обновить
      </button>
    </div>

    <p v-if="pending" class="text-slate-500">Загрузка…</p>
    <p v-else-if="error" class="rounded bg-red-50 p-4 text-red-700">
      Ошибка загрузки: {{ error.message }}
    </p>
    <p v-else-if="!campaigns?.length" class="rounded border border-dashed border-slate-300 p-8 text-center text-slate-500">
      Кампаний пока нет.
      <NuxtLink to="/campaigns/new" class="text-blue-600 hover:underline">Создать первую</NuxtLink>
    </p>

    <div v-else class="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-slate-500">
          <tr>
            <th class="px-4 py-3 font-medium">Название</th>
            <th class="px-4 py-3 font-medium">GEO</th>
            <th class="px-4 py-3 font-medium">Keitaro ID</th>
            <th class="px-4 py-3 font-medium">Создана</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in campaigns" :key="c.id" class="border-t border-slate-100 hover:bg-slate-50">
            <td class="px-4 py-3 font-medium">{{ c.name }}</td>
            <td class="px-4 py-3">{{ c.geo }}</td>
            <td class="px-4 py-3 text-slate-500">#{{ c.keitaroCampaignId }}</td>
            <td class="px-4 py-3 text-slate-500">{{ c.createdAt }}</td>
            <td class="px-4 py-3 text-right">
              <NuxtLink :to="`/campaigns/${c.id}`" class="text-blue-600 hover:underline">Открыть</NuxtLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
