import { useQuery } from '@tanstack/react-query'
import { createFeatureApiClient } from '@/lib/api'
import type {
  CollectionResponse,
  CaseDetailResponse,
  PaymentDetailResponse,
  CollectionFilters,
} from './types'

const client = createFeatureApiClient('finance')

export function useCollectionContracts(
  filters: CollectionFilters & { page?: number; page_size?: number }
) {
  return useQuery<CollectionResponse>({
    queryKey: ['collection', 'contracts', filters],
    queryFn: () =>
      client.get('contracts', { searchParams: filters as Record<string, string> }).json<CollectionResponse>(),
  })
}

export function useCaseDetails(contractId: number | null, caseName?: string) {
  return useQuery<CaseDetailResponse>({
    queryKey: ['collection', 'cases', contractId, caseName],
    queryFn: () =>
      client
        .get(`cases/${contractId}`, { searchParams: caseName ? { case_name: caseName } : {} })
        .json<CaseDetailResponse>(),
    enabled: !!contractId,
  })
}

export function usePaymentRecords(filters: CollectionFilters & { page?: number; page_size?: number }) {
  return useQuery<PaymentDetailResponse>({
    queryKey: ['collection', 'records', filters],
    queryFn: () =>
      client.get('records', { searchParams: filters as Record<string, string> }).json<PaymentDetailResponse>(),
    enabled: !!filters.contract_id || !!filters.case_id,
  })
}

export function getExportUrl(filters: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) params.set(k, String(v))
  })
  return `/api/v1/finance/export?${params.toString()}`
}
