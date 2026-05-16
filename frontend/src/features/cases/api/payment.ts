import { api } from '@/lib/api'
import type { CasePaymentRecord, PaymentRecordCategory, PaymentSummary } from '../types'

export interface PaymentRecordInput {
  case_id: number
  category_id: number
  amount: string | number
  record_date: string
  is_income: boolean
  payment_method?: string
  payer_payee_name?: string
  case_number_id?: number
  has_receipt?: boolean
  receipt_note?: string
  description?: string
}

export interface PaymentRecordUpdateInput {
  category_id?: number
  amount?: string | number
  record_date?: string
  is_income?: boolean
  payment_method?: string
  payer_payee_name?: string
  case_number_id?: number
  has_receipt?: boolean
  receipt_note?: string
  description?: string
}

export interface PaymentCategoryInput {
  name: string
  is_income: boolean
}

async function listCasePayments(caseId: number): Promise<CasePaymentRecord[]> {
  const response = await api.get<CasePaymentRecord[]>(`/api/cases/case/${caseId}/payments`)
  return response.data
}

async function getPaymentSummary(caseId: number): Promise<PaymentSummary> {
  const response = await api.get<PaymentSummary>(`/api/cases/case/${caseId}/payments/summary`)
  return response.data
}

async function createPayment(data: PaymentRecordInput): Promise<CasePaymentRecord> {
  const response = await api.post<CasePaymentRecord>('/api/cases/payments', data)
  return response.data
}

async function updatePayment(recordId: number, data: PaymentRecordUpdateInput): Promise<CasePaymentRecord> {
  const response = await api.put<CasePaymentRecord>(`/api/cases/payments/${recordId}`, data)
  return response.data
}

async function deletePayment(recordId: number): Promise<{ success: boolean }> {
  const response = await api.delete(`/api/cases/payments/${recordId}`)
  return response.data
}

async function listCategories(isIncome?: boolean): Promise<PaymentRecordCategory[]> {
  const params = isIncome !== undefined ? { is_income: isIncome } : {}
  const response = await api.get<PaymentRecordCategory[]>('/api/cases/payment-categories', { params })
  return response.data
}

async function createCategory(data: PaymentCategoryInput): Promise<PaymentRecordCategory> {
  const response = await api.post<PaymentRecordCategory>('/api/cases/payment-categories', data)
  return response.data
}

async function deleteCategory(categoryId: number): Promise<{ success: boolean }> {
  const response = await api.delete(`/api/cases/payment-categories/${categoryId}`)
  return response.data
}

async function initCategories(): Promise<{ status: string }> {
  const response = await api.post('/api/cases/payment-categories/init')
  return response.data
}

export const paymentApi = {
  listCasePayments,
  getPaymentSummary,
  createPayment,
  updatePayment,
  deletePayment,
  listCategories,
  createCategory,
  deleteCategory,
  initCategories,
}
