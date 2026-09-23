import { useMutation } from '@tanstack/react-query'
import { matchContractors } from '../api/match'

export function useMatch() {
  return useMutation({ mutationFn: matchContractors })
}
