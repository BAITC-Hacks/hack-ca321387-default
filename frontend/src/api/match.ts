import { ApiError, apiClient, mockMode } from './client'
import type { Contractor, EvidenceLedger, MatchResponse, SearchParams } from '../types/match'

type RawCandidate = Partial<Contractor> & {
  anon_name?: string
  price_from_kzt?: number
  category?: string
  evidence?: EvidenceLedger
}

interface RawMatchResponse extends Partial<Omit<MatchResponse, 'status' | 'results'>> {
  status?: string
  outcome?: string
  results?: RawCandidate[]
  candidates?: RawCandidate[]
}

function normalizeResponse(raw: RawMatchResponse): MatchResponse {
  const rawStatus = raw.status || raw.outcome
  const status = rawStatus === 'category_absent_in_city' ? 'category_not_found'
    : rawStatus === 'constraints_failed' ? 'no_match' : rawStatus
  if (status !== 'matched' && status !== 'category_not_found' && status !== 'no_match') {
    throw new ApiError('Сервер вернул неизвестный статус подбора.', 502)
  }
  const candidates = raw.results || raw.candidates || []
  const results = candidates.map((item) => {
    const name = item.name || item.anon_name
    const price = item.price ?? item.price_from_kzt
    if (!item.id || !name || price === undefined || item.score === undefined || !item.evidence || !item.explanation) {
      throw new ApiError('Сервер вернул неполную карточку подрядчика.', 502)
    }
    return {
      ...item,
      id: item.id,
      name,
      categories: item.categories || (item.category ? [item.category] : []),
      city: item.city || '',
      price,
      score: item.score,
      semantic_score: item.semantic_score ?? item.evidence.semantic?.score ?? 0,
      synthetic: item.synthetic ?? false,
      evidence: item.evidence,
      explanation: item.explanation,
    } satisfies Contractor
  })
  return {
    status, results: results.slice(0, 3), diagnostics: raw.diagnostics,
    availability: raw.availability, total_eligible: raw.total_eligible,
    model_info: raw.model_info,
  }
}

export async function matchContractors(input: SearchParams): Promise<MatchResponse> {
  if (mockMode) {
    const { mockMatch } = await import('../mocks/engine')
    return mockMatch(input)
  }
  const response = await apiClient<RawMatchResponse>('/match', { method: 'POST', body: JSON.stringify(input) })
  return normalizeResponse(response)
}
