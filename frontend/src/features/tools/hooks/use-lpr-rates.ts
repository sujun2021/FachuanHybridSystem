/**
 * useLprRates Hook
 * 获取 LPR 利率列表
 */

import { useQuery } from '@tanstack/react-query'
import { lprApi_ } from '../api'

export function useLprRates() {
  return useQuery({
    queryKey: ['lpr-rates'],
    queryFn: () => lprApi_.listRates(12),
    staleTime: 60 * 60 * 1000,
  })
}

export default useLprRates
