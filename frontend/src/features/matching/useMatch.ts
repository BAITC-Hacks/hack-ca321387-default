import { useMutation } from '@tanstack/react-query'
import { matchContractors } from '../../shared/api/match.api'

export function useMatch() {
  return useMutation({ mutationFn: matchContractors })
}
