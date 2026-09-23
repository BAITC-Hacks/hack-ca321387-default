import { ApiError, apiClient, mockMode } from './client'
import { FALLBACK_METADATA } from '../../features/search/search.constants'
import type { Metadata } from '../types/match'

export async function getMetadata(): Promise<Metadata> {
  if (import.meta.env.DEV && mockMode) {
    const { mockMetadata } = await import('../../mocks/engine')
    return mockMetadata
  }
  try {
    return await apiClient<Metadata>('/meta/options')
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return FALLBACK_METADATA
    throw error
  }
}
