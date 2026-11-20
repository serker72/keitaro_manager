<script setup lang="ts">
const props = defineProps<{
  stream: StreamInfo
  availableOffers: OfferOption[]
}>()

const emit = defineEmits<{
  push: [streamId: number, offers: StreamOfferRow[]]
}>()

const savedOffers = ref<StreamOfferRow[]>(clone(props.stream.offers))
const draftOffers = ref<StreamOfferRow[]>(clone(props.stream.offers))
const selectedOfferId = ref<number>(0)
const editingOfferId = ref<number | null>(null)
const editingValue = ref<string>('')
const pushing = ref(false)
const pushError = ref<string | null>(null)

function clone(rows: StreamOfferRow[]): StreamOfferRow[] {
  return rows.map((o) => ({ ...o }))
}

const dirty = computed(() => isDirty(savedOffers.value, draftOffers.value))
const sharesSum = computed(() => activeSharesSum(draftOffers.value))
const sharesValid = computed(() => sharesSum.value === 100)

const activeOffers = computed(() => draftOffers.value.filter((o) => !o.isRemoved))
const removedOffers = computed(() => draftOffers.value.filter((o) => o.isRemoved))

const addableOffers = computed(() => {
  const used = new Set(draftOffers.value.filter((o) => !o.isRemoved).map((o) => o.offerId))
  return props.availableOffers.filter((o) => !used.has(o.id))
})

function recalc() {
  draftOffers.value = recalculateWeights(draftOffers.value)
}

function addOffer() {
  if (!selectedOfferId.value) return
  const offer = props.availableOffers.find((o) => o.id === selectedOfferId.value)
  if (!offer) return
  const existing = draftOffers.value.find((o) => o.offerId === offer.id)
  if (existing) {
    existing.isRemoved = false
  } else {
    draftOffers.value.push({
      offerId: offer.id,
      offerName: offer.name,
      share: 0,
      isPinned: false,
      isRemoved: false,
      previewUrl: offer.previewPath,
    })
  }
  selectedOfferId.value = 0
  recalc()
}

function removeOffer(offerId: number) {
  const row = draftOffers.value.find((o) => o.offerId === offerId)
  if (!row) return
  row.isRemoved = true
  row.isPinned = false
  recalc()
}

function bringBack(offerId: number) {
  const row = draftOffers.value.find((o) => o.offerId === offerId)
  if (!row) return
  row.isRemoved = false
  recalc()
}

function togglePin(offerId: number) {
  const row = draftOffers.value.find((o) => o.offerId === offerId)
  if (!row || row.isRemoved) return
  row.isPinned = !row.isPinned
  recalc()
}

function startEditShare(row: StreamOfferRow) {
  if (row.isRemoved) return
  editingOfferId.value = row.offerId
  editingValue.value = String(row.share)
}

function commitEditShare() {
  if (editingOfferId.value === null) return
  const row = draftOffers.value.find((o) => o.offerId === editingOfferId.value)
  const parsed = Number.parseInt(editingValue.value, 10)
  if (row && Number.isFinite(parsed)) {
    row.share = Math.min(100, Math.max(0, parsed))
  }
  editingOfferId.value = null
  recalc()
}

function cancel() {
  draftOffers.value = clone(savedOffers.value)
  editingOfferId.value = null
  pushError.value = null
}

async function push() {
  if (!sharesValid.value || pushing.value) return
  pushing.value = true
  pushError.value = null
  try {
    emit('push', props.stream.streamId, clone(draftOffers.value))
  } finally {
    pushing.value = false
  }
}

function applySaved(rows: StreamOfferRow[]) {
  savedOffers.value = clone(rows)
  draftOffers.value = clone(rows)
}

defineExpose({ applySaved })
</script>

<template>
  <div
    class="rounded-lg border bg-white transition-colors"
    :class="dirty ? 'border-amber-300 bg-amber-50/60' : 'border-slate-200'"
  >
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
      <div class="flex items-center gap-3">
        <span class="font-medium">{{ stream.name }}</span>
        <span class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">stream_id {{ stream.streamId }}</span>
        <span class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{{ stream.type }}</span>
      </div>
      <div v-if="dirty" class="flex items-center gap-2">
        <span class="text-xs text-amber-700">Несохранённые изменения</span>
        <button
          class="rounded bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
          :disabled="!sharesValid || pushing"
          :title="sharesValid ? 'Отправить в Keitaro' : `Сумма весов ${sharesSum}%, нужно 100%`"
          @click="push"
        >
          PUSH TO KT
        </button>
        <button class="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs hover:bg-slate-50" @click="cancel">
          CANCEL
        </button>
      </div>
    </div>

    <p v-if="dirty && !sharesValid" class="border-b border-amber-200 bg-amber-100/70 px-4 py-2 text-xs text-amber-800">
      Сумма весов активных офферов: {{ sharesSum }}% — должно быть ровно 100%.
    </p>
    <p v-if="pushError" class="border-b border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">{{ pushError }}</p>

    <table class="w-full text-sm">
      <thead class="bg-slate-50 text-left text-slate-500">
        <tr>
          <th class="px-4 py-2 font-medium">Offer</th>
          <th class="w-24 px-4 py-2 font-medium">Share</th>
          <th class="w-20 px-4 py-2 font-medium">Stats</th>
          <th class="w-20 px-4 py-2 font-medium">Trends</th>
          <th class="w-40 px-4 py-2 text-right font-medium">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in activeOffers" :key="row.offerId" class="border-t border-slate-100">
          <td class="px-4 py-2">
            <div class="flex items-center gap-2">
              <span>{{ row.offerName }}</span>
              <a
                v-if="row.previewUrl"
                :href="row.previewUrl"
                target="_blank"
                rel="noopener"
                class="text-xs text-blue-600 hover:underline"
              >
                preview
              </a>
            </div>
          </td>
          <td class="px-4 py-2">
            <input
              v-if="editingOfferId === row.offerId"
              v-model="editingValue"
              type="number"
              min="0"
              max="100"
              class="w-16 rounded border border-slate-300 px-1 py-0.5 text-sm"
              @blur="commitEditShare"
              @keyup.enter="commitEditShare"
              @keyup.esc="editingOfferId = null"
            >
            <button
              v-else
              class="rounded px-1 text-blue-600 hover:bg-blue-50 hover:underline"
              :title="'Изменить вес'"
              @click="startEditShare(row)"
            >
              {{ row.share }}%
            </button>
          </td>
          <td class="px-4 py-2 text-slate-400">—</td>
          <td class="px-4 py-2 text-slate-400">—</td>
          <td class="px-4 py-2">
            <div class="flex justify-end gap-2">
              <button
                class="rounded border px-2 py-1 text-xs"
                :class="row.isPinned ? 'border-amber-400 bg-amber-100 text-amber-800' : 'border-slate-300 hover:bg-slate-50'"
                :title="row.isPinned ? 'Снять pin' : 'Запинить вес'"
                @click="togglePin(row.offerId)"
              >
                {{ row.isPinned ? 'PINNED' : 'PIN' }}
              </button>
              <button
                class="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                @click="removeOffer(row.offerId)"
              >
                REMOVE
              </button>
            </div>
          </td>
        </tr>

        <tr v-for="row in removedOffers" :key="`removed-${row.offerId}`" class="border-t border-slate-100 text-slate-400">
          <td class="px-4 py-2">
            <span>{{ row.offerName }}</span>
            <span class="ml-2 text-xs italic">(removed)</span>
          </td>
          <td class="px-4 py-2">0%</td>
          <td class="px-4 py-2">—</td>
          <td class="px-4 py-2">—</td>
          <td class="px-4 py-2 text-right">
            <button
              class="rounded border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
              @click="bringBack(row.offerId)"
            >
              BRING BACK
            </button>
          </td>
        </tr>

        <tr v-if="!activeOffers.length && !removedOffers.length">
          <td colspan="5" class="px-4 py-4 text-center text-slate-400">Офферов нет</td>
        </tr>
      </tbody>
    </table>

    <div class="flex items-center gap-2 border-t border-slate-200 px-4 py-3">
      <select v-model.number="selectedOfferId" class="rounded border border-slate-300 px-2 py-1.5 text-sm">
        <option :value="0">— выберите оффер —</option>
        <option v-for="o in addableOffers" :key="o.id" :value="o.id">{{ o.name }}</option>
      </select>
      <button
        class="rounded bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
        :disabled="!selectedOfferId"
        @click="addOffer"
      >
        ADD
      </button>
      <span class="ml-auto text-xs" :class="sharesValid ? 'text-slate-500' : 'text-amber-700'">
        Сумма: {{ sharesSum }}%
      </span>
    </div>
  </div>
</template>
