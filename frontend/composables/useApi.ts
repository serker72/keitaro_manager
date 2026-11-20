/** Типизированный API-слой поверх $fetch (проксируется на бэкенд через routeRules). */

export function useApi() {
  const request = <T>(url: string, opts: Parameters<typeof $fetch>[1] = {}) => $fetch<T>(url, opts)

  return {
    getDictionaries: () => request<DictionariesResponse>('/api/dictionaries'),

    listCampaigns: () => request<CampaignListItem[]>('/api/campaigns'),

    createCampaign: (body: CampaignCreateRequest) =>
      request<CampaignListItem>('/api/campaigns', { method: 'POST', body }),

    getStreams: (campaignId: number, sync = false) =>
      request<StreamsResponse>(`/api/campaigns/${campaignId}/streams`, { query: { sync } }),

    pushStream: (campaignId: number, streamId: number, body: PushOffersRequest) =>
      request<StreamsResponse>(`/api/campaigns/${campaignId}/streams/${streamId}/push`, {
        method: 'PUT',
        body,
      }),
  }
}
