<script setup lang="ts">
const route = useRoute()
const api = useApi()

const campaignId = computed(() => Number(route.params.id))
const campaign = ref<CampaignListItem | null>(null)
const streams = ref<StreamInfo[]>([])
const dictionaries = ref<DictionariesResponse | null>(null)
const loading = ref(true)
const syncing = ref(false)
const pageError = ref<string | null>(null)
const pushMessage = ref<string | null>(null)

type StreamOffersRef = { applySaved: (rows: StreamOfferRow[]) => void }
const streamRefs = new Map<number, StreamOffersRef>()

const runtimeConfig = useRuntimeConfig()
const keitaroLink = computed(() => {
  const base = String(runtimeConfig.public.keitaroAdminUrl || '').replace(/\/$/, '')
  if (!base || !campaign.value) return null
  return `${base}/#campaigns/${campaign.value.keitaroCampaignId}`
})

async function load(sync = false) {
  pageError.value = null
  try {
    if (sync) syncing.value = true
    const [list, data, dict] = await Promise.all([
      campaign.value ? Promise.resolve([campaign.value]) : api.listCampaigns(),
      api.getStreams(campaignId.value, sync),
      dictionaries.value ? Promise.resolve(dictionaries.value) : api.getDictionaries(),
    ])
    campaign.value = (list as CampaignListItem[]).find((c) => c.id === campaignId.value) || null
    streams.value = data.streams
    dictionaries.value = dict as DictionariesResponse
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string }; message?: string }
    pageError.value = err.data?.detail || err.message || 'Ошибка загрузки'
  } finally {
    loading.value = false
    syncing.value = false
  }
}

await load(false)

async function fetchFromKt() {
  pushMessage.value = null
  await load(true)
  pushMessage.value = 'Потоки синхронизированы с Keitaro'
  setTimeout(() => (pushMessage.value = null), 3000)
}

async function onPush(streamId: number, offers: StreamOfferRow[]) {
  pushMessage.value = null
  pageError.value = null
  try {
    const result = await api.pushStream(campaignId.value, streamId, { offers })
    streams.value = result.streams
    const updated = result.streams.find((s) => s.streamId === streamId)
    if (updated) streamRefs.get(streamId)?.applySaved(updated.offers)
    pushMessage.value = 'Отправлено в Keitaro'
    setTimeout(() => (pushMessage.value = null), 3000)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string }; message?: string }
    pageError.value = err.data?.detail || err.message || 'Не удалось отправить в Keitaro'
  }
}

function setRef(streamId: number, el: unknown) {
  if (el) streamRefs.set(streamId, el as StreamOffersRef)
}
</script>

<template>
  <section>
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <NuxtLink to="/" class="text-sm text-slate-500 hover:text-slate-900">← К списку кампаний</NuxtLink>
        <h1 class="mt-1 text-2xl font-semibold">
          {{ campaign?.name || `Кампания #${campaignId}` }}
          <span v-if="campaign" class="ml-2 text-sm font-normal text-slate-500">
            {{ campaign.geo }} · KT #{{ campaign.keitaroCampaignId }}
          </span>
        </h1>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
          :disabled="syncing"
          @click="fetchFromKt"
        >
          {{ syncing ? 'Синхронизация…' : 'FETCH STREAMS FROM KT' }}
        </button>
        <a
          v-if="keitaroLink"
          :href="keitaroLink"
          target="_blank"
          rel="noopener"
          class="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
        >
          VIEW IN KT
        </a>
      </div>
    </div>

    <p v-if="loading" class="text-slate-500">Загрузка потоков…</p>
    <p v-else-if="pageError" class="mb-4 rounded bg-red-50 p-4 text-red-700">{{ pageError }}</p>
    <p v-else-if="pushMessage" class="mb-4 rounded bg-emerald-50 p-3 text-sm text-emerald-700">{{ pushMessage }}</p>

    <div v-if="!loading" class="space-y-4">
      <template v-for="stream in streams" :key="stream.streamId">
        <!-- Поток без офферов: компактная строка -->
        <div
          v-if="!stream.offers.length"
          class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3"
        >
          <div class="flex flex-wrap items-center gap-3">
            <span class="font-medium">{{ stream.name }}</span>
            <span class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">stream_id {{ stream.streamId }}</span>
            <span v-if="stream.filterDescription" class="text-sm text-slate-600">{{ stream.filterDescription }}</span>
            <span v-if="stream.actionPayload" class="text-sm text-slate-400">→ {{ stream.actionPayload }}</span>
          </div>
          <span class="text-xs text-slate-500">клики: {{ stream.clicks ?? '—' }}</span>
        </div>

        <!-- Поток с офферами: таблица редактора -->
        <StreamOffers
          v-else
          :ref="(el) => setRef(stream.streamId, el)"
          :stream="stream"
          :available-offers="dictionaries?.offers || []"
          @push="onPush"
        />
      </template>

      <p v-if="!streams.length" class="rounded border border-dashed border-slate-300 p-8 text-center text-slate-500">
        У кампании нет потоков. Нажмите FETCH STREAMS FROM KT.
      </p>
    </div>
  </section>
</template>
