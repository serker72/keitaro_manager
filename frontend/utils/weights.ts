/** Пересчёт весов — зеркало backend-функции recalculate_weights (единая формула). */

export function recalculateWeights(offers: StreamOfferRow[]): StreamOfferRow[] {
  const activeUnpinned = offers.filter((o) => !o.isRemoved && !o.isPinned)
  const pinnedSum = offers.filter((o) => o.isPinned && !o.isRemoved).reduce((sum, o) => sum + o.share, 0)
  const remaining = Math.max(0, 100 - pinnedSum)

  const count = activeUnpinned.length
  const base = count ? Math.floor(remaining / count) : 0
  const mod = count ? remaining % count : 0

  let unpinnedIdx = 0
  return offers.map((o) => {
    if (o.isRemoved) return { ...o, share: 0 }
    if (o.isPinned) return { ...o }
    const share = base + (unpinnedIdx < mod ? 1 : 0)
    unpinnedIdx += 1
    return { ...o, share }
  })
}

export function activeSharesSum(offers: StreamOfferRow[]): number {
  return offers.filter((o) => !o.isRemoved).reduce((sum, o) => sum + o.share, 0)
}

export function isDirty(saved: StreamOfferRow[], draft: StreamOfferRow[]): boolean {
  if (saved.length !== draft.length) return true
  const key = (o: StreamOfferRow) => `${o.offerId}`
  const savedMap = new Map(saved.map((o) => [key(o), o]))
  for (const d of draft) {
    const s = savedMap.get(key(d))
    if (!s) return true
    if (s.share !== d.share || s.isPinned !== d.isPinned || s.isRemoved !== d.isRemoved) return true
  }
  return false
}
