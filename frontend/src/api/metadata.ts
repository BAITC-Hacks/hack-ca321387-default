import { apiClient, mockMode } from './client'
import type { Metadata } from '../types/match'

export async function getMetadata(): Promise<Metadata> {
  if (import.meta.env.DEV && mockMode) {
    const { mockMetadata } = await import('../mocks/engine')
    return mockMetadata
  }
  return apiClient<Metadata>('/meta/options')
}
