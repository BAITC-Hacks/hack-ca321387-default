import { apiClient } from '../../shared/api/client'

export interface ExtractedFields {
  city: string | null
  date: string | null
  event_type: string | null
  category: string | null
  budget: number | null
  language: string | null
  duration: number | null
}

export interface ExtractionResponse {
  fields: ExtractedFields
  evidence: Record<string, string>
  missing: string[]
  provider: 'openai' | 'local'
}

export function extractSearch(text: string): Promise<ExtractionResponse> {
  return apiClient('/search/extract', {
    method: 'POST', body: JSON.stringify({ text }), signal: AbortSignal.timeout(80_000),
  })
}
