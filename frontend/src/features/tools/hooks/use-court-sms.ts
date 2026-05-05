/**
 * useCourtSms Hooks
 * 法院短信数据查询
 */

import { useQuery } from '@tanstack/react-query'
import { courtSmsApi, type CourtSMSListParams } from '../api/court-sms'

export function useCourtSmsList(params?: CourtSMSListParams) {
  return useQuery({
    queryKey: ['court-sms', params],
    queryFn: () => courtSmsApi.list(params),
    staleTime: 30 * 1000,
  })
}
