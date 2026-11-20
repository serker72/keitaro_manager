<script setup lang="ts">
const api = useApi()
const router = useRouter()

const { data: dict, pending: dictPending, error: dictError } = await useAsyncData('dictionaries', () =>
  api.getDictionaries(),
)

const form = reactive<CampaignCreateRequest>({
  name: '',
  geo: '',
  domainId: 0,
  groupId: 0,
  trafficSourceId: 0,
  offerId: 0,
})

const submitting = ref(false)
const submitError = ref<string | null>(null)

watchEffect(() => {
  if (!dict.value) return
  if (!form.domainId && dict.value.domains[0]) form.domainId = dict.value.domains[0].id
  if (!form.groupId && dict.value.groups[0]) form.groupId = dict.value.groups[0].id
  if (!form.trafficSourceId && dict.value.trafficSources[0]) form.trafficSourceId = dict.value.trafficSources[0].id
  if (!form.offerId && dict.value.offers[0]) form.offerId = dict.value.offers[0].id
})

const isValid = computed(
  () =>
    form.name.trim().length > 0 &&
    /^[A-Za-z]{2,10}$/.test(form.geo.trim()) &&
    form.domainId > 0 &&
    form.groupId > 0 &&
    form.trafficSourceId > 0 &&
    form.offerId > 0,
)

async function submit() {
  if (!isValid.value || submitting.value) return
  submitting.value = true
  submitError.value = null
  try {
    const created = await api.createCampaign({
      ...form,
      name: form.name.trim(),
      geo: form.geo.trim().toUpperCase(),
    })
    await router.push(`/campaigns/${created.id}`)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string }; message?: string }
    submitError.value = err.data?.detail || err.message || 'Не удалось создать кампанию'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="max-w-2xl">
    <h1 class="mb-6 text-2xl font-semibold">Создаватор кампаний</h1>

    <p v-if="dictPending" class="text-slate-500">Загрузка справочников…</p>
    <p v-else-if="dictError" class="rounded bg-red-50 p-4 text-red-700">
      Ошибка загрузки справочников: {{ dictError.message }}
    </p>

    <form v-else class="space-y-4 rounded-lg border border-slate-200 bg-white p-6" @submit.prevent="submit">
      <div>
        <label class="mb-1 block text-sm font-medium">Название кампании</label>
        <input
          v-model="form.name"
          type="text"
          placeholder="Например: US Flexacil"
          class="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        >
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium">GEO-код страны</label>
        <input
          v-model="form.geo"
          type="text"
          maxlength="10"
          placeholder="US"
          class="w-full rounded border border-slate-300 px-3 py-2 text-sm uppercase focus:border-slate-500 focus:outline-none"
        >
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium">Домен</label>
        <select v-model.number="form.domainId" class="w-full rounded border border-slate-300 px-3 py-2 text-sm">
          <option v-for="d in dict!.domains" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium">Группа кампаний</label>
        <select v-model.number="form.groupId" class="w-full rounded border border-slate-300 px-3 py-2 text-sm">
          <option v-for="g in dict!.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium">Источник трафика</label>
        <select v-model.number="form.trafficSourceId" class="w-full rounded border border-slate-300 px-3 py-2 text-sm">
          <option v-for="s in dict!.trafficSources" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium">Оффер (Flow 2, 100%)</label>
        <select v-model.number="form.offerId" class="w-full rounded border border-slate-300 px-3 py-2 text-sm">
          <option v-for="o in dict!.offers" :key="o.id" :value="o.id">{{ o.name }}</option>
        </select>
      </div>

      <p v-if="submitError" class="rounded bg-red-50 p-3 text-sm text-red-700">{{ submitError }}</p>

      <div class="flex items-center gap-3 pt-2">
        <button
          type="submit"
          class="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          :disabled="!isValid || submitting"
        >
          {{ submitting ? 'Создание…' : 'Создать кампанию' }}
        </button>
        <NuxtLink to="/" class="text-sm text-slate-500 hover:text-slate-900">Отмена</NuxtLink>
      </div>
    </form>
  </section>
</template>
