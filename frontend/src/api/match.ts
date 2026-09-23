import { ApiError, apiClient, mockMode } from './client'
import type { MatchResponse, SearchParams } from '../types/match'

export function normalizeResponse(raw: MatchResponse): MatchResponse {
  const validScore = (score: number | null) => score === null || (Number.isFinite(score) && score >= 0 && score <= 1)
  if (!raw || !['matched', 'category_not_found', 'no_match'].includes(raw.status) || !Array.isArray(raw.results)
    || raw.results.length > 3 || (raw.status === 'matched') !== (raw.results.length > 0)
    || !raw.diagnostics || !raw.model_info || !Number.isInteger(raw.total_eligible)
    || raw.total_eligible < raw.results.length) {
    throw new ApiError('Сервер вернул некорректный результат подбора.', 502, 'invalid_response')
  }
  for (const item of raw.results) {
    if (!item.id || !item.name || !Number.isFinite(item.price) || item.score === null || !validScore(item.score)
      || !validScore(item.semantic_score) || !item.evidence || !item.explanation
      || !Array.isArray(item.categories) || !Array.isArray(item.languages)
      || !item.score_breakdown || !item.score_weights
      || ['date', 'budget', 'format', 'language', 'duration', 'semantic'].some((key) => !(key in item.evidence))) {
      throw new ApiError('Сервер вернул неполную карточку подрядчика.', 502, 'invalid_response')
    }
  }
  return raw // Preserve the backend's order and nulls; never invent missing scores.
}

export async function matchContractors(input: SearchParams): Promise<MatchResponse> {
  const request = { ...input, language: input.language || null, duration: input.duration ?? null }
  if (import.meta.env.DEV && mockMode) {
    const { mockMatch } = await import('../mocks/engine')
    return normalizeResponse(mockMatch(request))
  }
  return normalizeResponse(await apiClient<MatchResponse>('/match', { method: 'POST', body: JSON.stringify(request) }))
}
