import { useQuery } from '@tanstack/react-query'
import { getMetadata } from '../api/metadata'

export function useMetadata() {
  return useQuery({ queryKey: ['metadata'], queryFn: getMetadata, retry: 1, staleTime: 60_000 })
}
