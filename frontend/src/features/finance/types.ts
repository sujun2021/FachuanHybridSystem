/** 客户收款看板 TypeScript 类型 */

export interface ContractSummary {
  contract_id: number
  contract_name: string
  client_name: string
  fee_mode: string
  fee_mode_display: string
  fixed_amount: number | null
  total_received: number
  balance: number
  case_count: number
  received_rate: number
}

export interface CaseDetail {
  case_id: number
  case_name: string
  case_status: string
  attorney_fee_received: number
  case_income: number
  case_expense: number
  net_income: number
  payment_count: number
}

export interface PaymentRecord {
  id: number
  source: 'contract_payment' | 'case_payment_record'
  direction: 'income' | 'expense'
  amount: number
  purpose: string
  purpose_display: string
  received_date: string
  contract_name: string
  case_name: string
  client_name: string
  note: string
}

export interface CollectionResponse {
  total_expected: number
  total_received: number
  total_balance: number
  overall_rate: number
  contracts: ContractSummary[]
  total: number
  page: number
  page_size: number
}

export interface CaseDetailResponse {
  cases: CaseDetail[]
  total: number
}

export interface PaymentDetailResponse {
  records: PaymentRecord[]
  total: number
}

export interface CollectionFilters {
  client_id?: number
  contract_id?: number
  case_id?: number
  case_name?: string
  fee_mode?: string
  start_date?: string
  end_date?: string
}

export type ExportLevel = 'contract' | 'case' | 'detail'

export const FEE_MODE_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'FIXED', label: '固定收费' },
  { value: 'SEMI_RISK', label: '半风险收费' },
  { value: 'FULL_RISK', label: '全风险收费' },
  { value: 'CUSTOM', label: '自定义' },
]

export const EXPORT_FIELDS: Record<ExportLevel, { key: string; label: string }[]> = {
  contract: [
    { key: 'contract_name', label: '合同名称' },
    { key: 'client_name', label: '客户名称' },
    { key: 'fee_mode_display', label: '收费模式' },
    { key: 'fixed_amount', label: '合同应收' },
    { key: 'total_received', label: '已收金额' },
    { key: 'balance', label: '未收余额' },
    { key: 'received_rate', label: '回款率' },
    { key: 'case_count', label: '案件数' },
  ],
  case: [
    { key: 'case_name', label: '案件名称' },
    { key: 'case_status', label: '案件状态' },
    { key: 'attorney_fee_received', label: '已收律师费' },
    { key: 'case_income', label: '总收入' },
    { key: 'case_expense', label: '总支出' },
    { key: 'net_income', label: '净收入' },
    { key: 'payment_count', label: '收款笔数' },
  ],
  detail: [
    { key: 'received_date', label: '收款日期' },
    { key: 'source', label: '来源' },
    { key: 'amount', label: '金额' },
    { key: 'purpose_display', label: '用途' },
    { key: 'contract_name', label: '合同名称' },
    { key: 'case_name', label: '案件名称' },
    { key: 'note', label: '备注' },
  ],
}
