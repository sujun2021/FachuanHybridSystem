import { useMutation } from '@tanstack/react-query'
import { lprApi_, type LprCalculateRequest, type LprCalculateResponse } from '../api'

export function useLprCalculate() {
  return useMutation<LprCalculateResponse, Error, LprCalculateRequest>({
    mutationFn: (body) => lprApi_.calculate(body),
  })
}
