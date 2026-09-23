import { apiClient } from './client'
import type { AvailabilityDay, MatchResponse, SearchParams } from '../types/match'

export interface DemoPreset {
  id: string
  title: string
  description: string
  query: SearchParams
  expected_status: 'matched' | 'no_match'
  eligible_count: number
  related_query: SearchParams | null
  related_eligible_count: number | null
}

export interface DemoPresetsResponse {
  data_version: string
  presets: DemoPreset[]
  omitted: Array<{ id: string; reason: string }>
}

export interface AvailabilityResponse {
  query: SearchParams
  date_from: string
  date_to: string
  days: AvailabilityDay[]
  recommended_date: string | null
  data_version: string
}

export interface ScoreComponentDetail {
  component: 'semantic' | 'lexical' | 'budget' | 'duration'
  state: 'active' | 'not_requested' | 'not_applicable' | 'unavailable'
  value: number | null
  weight: number | null
  contribution: number | null
  source_fields: string[]
  reason: string
}

export interface RankingDetail {
  candidate_id: string
  position: number
  score: number
  components: ScoreComponentDetail[]
}

export interface DetailedMatchResponse {
  query: SearchParams
  match: MatchResponse
  ranking: RankingDetail[]
  funnel: Array<{ stage: string; label: string; before: number; after: number; application: string; reason: string }>
  comparison: {
    price_note: string
    decisions: Array<{ higher_id: string; lower_id: string; decided_by: string; reason: string }>
  }
}

export function getDemoPresets(): Promise<DemoPresetsResponse> {
  return apiClient('/demo-presets')
}

export function getAvailability(query: SearchParams): Promise<AvailabilityResponse> {
  return apiClient('/availability', {
    method: 'POST',
    body: JSON.stringify({ query, days_before: 14, days_after: 14 }),
  })
}

export function getMatchDetails(query: SearchParams): Promise<DetailedMatchResponse> {
  return apiClient('/match/details', {
    method: 'POST', body: JSON.stringify(query), signal: AbortSignal.timeout(45_000),
  })
}
