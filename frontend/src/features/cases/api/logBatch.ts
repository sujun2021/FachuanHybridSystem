import { api } from '@/lib/api'
import type { CaseLog, CaseLogBatch, PaymentCategory } from '../types'

export interface LogBatchPreviewInput {
  case_ids: number[]
  content: string
  has_expense_split?: boolean
  expense_amount?: string | number
  expense_split_count?: number
}

export interface LogBatchPreviewItem {
  case_id: number
  case_name: string
  content_preview: string
  expense_amount: string | number | null
  has_expense_split: boolean
}

export interface LogBatchPreviewResult {
  total_count: number
  logs: LogBatchPreviewItem[]
  expense_per_case: string | number | null
  has_expense_split: boolean
  original_content: string
}

export interface LogBatchCreateInput {
  case_ids: number[]
  content: string
  reminder_type?: string
  reminder_time?: string
  has_expense_split?: boolean
  expense_amount?: string | number
  expense_category_id?: number
  expense_split_count?: number
  expense_record_date?: string
  expense_payment_method?: string
  expense_description?: string
}

async function previewBatchLog(data: LogBatchPreviewInput): Promise<LogBatchPreviewResult> {
  const response = await api.post<LogBatchPreviewResult>('/api/cases/batch-log/preview', data)
  return response.data
}

async function createBatchLog(data: LogBatchCreateInput): Promise<CaseLogBatch> {
  const response = await api.post<CaseLogBatch>('/api/cases/batch-log', data)
  return response.data
}

async function getBatchDetail(batchId: number): Promise<CaseLogBatch & { logs: CaseLog[] }> {
  const response = await api.get(`/api/cases/batch-log/${batchId}`)
  return response.data
}

async function listBatches(limit: number = 50): Promise<CaseLogBatch[]> {
  const response = await api.get<CaseLogBatch[]>('/api/cases/batch-log', { params: { limit } })
  return response.data
}

export const logBatchApi = {
  previewBatchLog,
  createBatchLog,
  getBatchDetail,
  listBatches,
}
