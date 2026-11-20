/** Глобальные типы, зеркалящие Pydantic-схемы бэкенда (camelCase). */

declare global {
  interface DomainOption {
    id: number
    name: string
  }

  interface GroupOption {
    id: number
    name: string
  }

  interface SourceOption {
    id: number
    name: string
  }

  interface OfferOption {
    id: number
    name: string
    previewPath: string | null
  }

  interface DictionariesResponse {
    domains: DomainOption[]
    groups: GroupOption[]
    trafficSources: SourceOption[]
    offers: OfferOption[]
  }

  interface CampaignCreateRequest {
    name: string
    geo: string
    domainId: number
    groupId: number
    trafficSourceId: number
    offerId: number
  }

  interface CampaignListItem {
    id: number
    keitaroCampaignId: number
    name: string
    geo: string
    createdAt: string
    updatedAt: string
  }

  interface StreamOfferRow {
    offerId: number
    offerName: string
    share: number
    isPinned: boolean
    isRemoved: boolean
    previewUrl?: string | null
  }

  interface StreamInfo {
    streamId: number
    name: string
    type: string
    state: string
    clicks: number | null
    filterDescription: string | null
    actionPayload: string | null
    previewUrl: string | null
    offers: StreamOfferRow[]
  }

  interface StreamsResponse {
    campaignId: number
    keitaroCampaignId: number
    streams: StreamInfo[]
  }

  interface PushOffersRequest {
    offers: StreamOfferRow[]
  }
}

export {}
