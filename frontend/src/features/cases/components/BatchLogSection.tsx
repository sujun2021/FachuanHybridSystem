import { useState, useEffect, useCallback } from 'react'
import { caseApi } from '../api'
import type { Case, PaymentRecordCategory, CaseLogBatch, CaseLog } from '../types'

interface BatchLogSectionProps {
  cases: Case[]
}

interface LogBatchPreviewItem {
  case_id: number
  case_name: string
  content_preview: string
  expense_amount: string | number | null
  has_expense_split: boolean
}

interface LogBatchPreviewResult {
  total_count: number
  logs: LogBatchPreviewItem[]
  expense_per_case: string | number | null
  has_expense_split: boolean
  original_content: string
}

export function BatchLogSection({ cases }: BatchLogSectionProps) {
  const [selectedCaseIds, setSelectedCaseIds] = useState<number[]>([])
  const [content, setContent] = useState('')
  const [preview, setPreview] = useState<LogBatchPreviewResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [expenseEnabled, setExpenseEnabled] = useState(false)
  const [expenseAmount, setExpenseAmount] = useState('')
  const [expenseCategoryId, setExpenseCategoryId] = useState<number>(0)
  const [expenseSplitCount, setExpenseSplitCount] = useState<number | undefined>(undefined)
  const [expenseRecordDate, setExpenseRecordDate] = useState(new Date().toISOString().split('T')[0])
  const [expensePaymentMethod, setExpensePaymentMethod] = useState('')
  const [expenseDescription, setExpenseDescription] = useState('')

  const [categories, setCategories] = useState<PaymentRecordCategory[]>([])
  const [batches, setBatches] = useState<CaseLogBatch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<CaseLogBatch | null>(null)

  const loadCategories = useCallback(async () => {
    try {
      const cats = await caseApi.listPaymentCategories()
      setCategories(cats)
    } catch (err) {
      console.error('Failed to load categories', err)
    }
  }, [])

  const loadBatches = useCallback(async () => {
    try {
      const batchList = await caseApi.listBatches(20)
      setBatches(batchList)
    } catch (err) {
      console.error('Failed to load batches', err)
    }
  }, [])

  useEffect(() => {
    loadCategories()
    loadBatches()
  }, [loadCategories, loadBatches])

  const handleCaseToggle = (caseId: number) => {
    setSelectedCaseIds(prev =>
      prev.includes(caseId)
        ? prev.filter(id => id !== caseId)
        : [...prev, caseId]
    )
  }

  const handleSelectAll = () => {
    if (selectedCaseIds.length === cases.length) {
      setSelectedCaseIds([])
    } else {
      setSelectedCaseIds(cases.map(c => c.id))
    }
  }

  const handlePreview = async () => {
    if (selectedCaseIds.length === 0) {
      setError('请选择至少一个案件')
      return
    }
    if (!content.trim()) {
      setError('请输入日志内容')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const result = await caseApi.previewBatchLog({
        case_ids: selectedCaseIds,
        content,
        has_expense_split: expenseEnabled,
        expense_amount: expenseEnabled ? Number(expenseAmount) : undefined,
        expense_split_count: expenseEnabled ? (expenseSplitCount || selectedCaseIds.length) : undefined,
      })
      setPreview(result)
      setShowPreview(true)
    } catch (err) {
      setError('预览失败')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (selectedCaseIds.length === 0 || !content.trim()) return

    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      const batch = await caseApi.createBatchLog({
        case_ids: selectedCaseIds,
        content,
        has_expense_split: expenseEnabled,
        expense_amount: expenseEnabled ? Number(expenseAmount) : undefined,
        expense_category_id: expenseEnabled ? expenseCategoryId || undefined : undefined,
        expense_split_count: expenseEnabled ? (expenseSplitCount || selectedCaseIds.length) : undefined,
        expense_record_date: expenseEnabled ? expenseRecordDate : undefined,
        expense_payment_method: expenseEnabled ? expensePaymentMethod : undefined,
        expense_description: expenseEnabled ? expenseDescription : undefined,
      })

      setSuccess(`成功创建 ${batch.success_count} 条日志${batch.fail_count > 0 ? `，失败 ${batch.fail_count} 条` : ''}`)
      setSelectedCaseIds([])
      setContent('')
      setPreview(null)
      setShowPreview(false)
      setExpenseEnabled(false)
      setExpenseAmount('')
      loadBatches()
    } catch (err) {
      setError('创建失败')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const expenseCategories = categories.filter(c => !c.is_income)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">批量日志</h3>
        <button
          onClick={() => setShowPreview(false)}
          className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
        >
          {showPreview ? '返回编辑' : '预览'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 bg-green-50 border border-green-200 text-green-600 rounded">
          {success}
        </div>
      )}

      {!showPreview ? (
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <label className="font-medium">选择案件 ({selectedCaseIds.length}/{cases.length})</label>
              <button
                onClick={handleSelectAll}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                {selectedCaseIds.length === cases.length ? '取消全选' : '全选'}
              </button>
            </div>
            <div className="max-h-40 overflow-y-auto border rounded p-2 space-y-1">
              {cases.map(c => (
                <label key={c.id} className="flex items-center py-1">
                  <input
                    type="checkbox"
                    checked={selectedCaseIds.includes(c.id)}
                    onChange={() => handleCaseToggle(c.id)}
                    className="mr-2"
                  />
                  <span className="text-sm">{c.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block font-medium mb-1">日志内容</label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2"
              rows={4}
              placeholder="输入统一的日志内容，如：今天下午2点开庭了，法官主要询问了xx等内容，花费100元，用时200分钟"
            />
          </div>

          <div className="p-4 bg-gray-50 rounded-lg">
            <label className="flex items-center mb-3">
              <input
                type="checkbox"
                checked={expenseEnabled}
                onChange={e => setExpenseEnabled(e.target.checked)}
                className="mr-2"
              />
              <span className="font-medium">包含费用分摊</span>
            </label>

            {expenseEnabled && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">费用总额</label>
                    <input
                      type="number"
                      step="0.01"
                      value={expenseAmount}
                      onChange={e => setExpenseAmount(e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1"
                      placeholder="如：100"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">费用类型</label>
                    <select
                      value={expenseCategoryId}
                      onChange={e => setExpenseCategoryId(Number(e.target.value))}
                      className="w-full rounded border border-gray-300 px-2 py-1"
                    >
                      <option value={0}>请选择</option>
                      {expenseCategories.map(c => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">分摊份数</label>
                    <input
                      type="number"
                      value={expenseSplitCount || selectedCaseIds.length}
                      onChange={e => setExpenseSplitCount(Number(e.target.value) || undefined)}
                      className="w-full rounded border border-gray-300 px-2 py-1"
                      placeholder={`默认${selectedCaseIds.length}`}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">发生日期</label>
                    <input
                      type="date"
                      value={expenseRecordDate}
                      onChange={e => setExpenseRecordDate(e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">支付方式</label>
                    <select
                      value={expensePaymentMethod}
                      onChange={e => setExpensePaymentMethod(e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1"
                    >
                      <option value="">请选择</option>
                      <option value="bank_transfer">银行转账</option>
                      <option value="cash">现金</option>
                      <option value="online_payment">线上支付</option>
                      <option value="other">其他</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">费用说明</label>
                  <input
                    type="text"
                    value={expenseDescription}
                    onChange={e => setExpenseDescription(e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1"
                    placeholder="如：交通费、差旅费等"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <button
              onClick={handlePreview}
              disabled={loading || selectedCaseIds.length === 0 || !content.trim()}
              className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              预览分拆效果
            </button>
          </div>
        </div>
      ) : (
        preview && (
          <div className="space-y-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-600">
                将分拆到 <span className="font-bold">{preview.total_count}</span> 个案件
                {preview.has_expense_split && preview.expense_per_case && (
                  <span>，每案件费用：<span className="font-bold">¥{Number(preview.expense_per_case).toFixed(2)}</span></span>
                )}
              </p>
            </div>

            <div className="max-h-96 overflow-y-auto border rounded">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">案件</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">分拆后内容</th>
                    {preview.has_expense_split && (
                      <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">分摊费用</th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {preview.logs.map(log => (
                    <tr key={log.case_id}>
                      <td className="px-3 py-2 text-sm font-medium">{log.case_name}</td>
                      <td className="px-3 py-2 text-sm text-gray-600">{log.content_preview}</td>
                      {preview.has_expense_split && (
                        <td className="px-3 py-2 text-sm text-right text-red-600">
                          ¥{Number(log.expense_amount || 0).toFixed(2)}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowPreview(false)}
                className="px-4 py-2 text-gray-600 border rounded hover:bg-gray-100"
              >
                返回修改
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {loading ? '创建中...' : '确认创建'}
              </button>
            </div>
          </div>
        )
      )}

      {batches.length > 0 && (
        <div className="mt-6">
          <h4 className="font-medium mb-3">最近批量日志</h4>
          <div className="space-y-2">
            {batches.slice(0, 5).map(batch => (
              <div
                key={batch.id}
                className="p-3 border rounded hover:bg-gray-50 cursor-pointer"
                onClick={() => setSelectedBatch(selectedBatch?.id === batch.id ? null : batch)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium">{batch.original_content.slice(0, 50)}...</span>
                    <span className="ml-2 text-xs text-gray-500">
                      {batch.success_count}/{batch.total_cases} 成功
                      {batch.has_expense_split && batch.expense_amount && (
                        <span className="ml-2">费用: ¥{Number(batch.expense_amount).toFixed(2)}</span>
                      )}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">{batch.created_at}</span>
                </div>
                {selectedBatch?.id === batch.id && (
                  <div className="mt-2 pt-2 border-t">
                    <p className="text-xs text-gray-600">
                      参与案件数: {batch.case_ids.length}
                      {batch.error_message && (
                        <span className="text-red-600 block mt-1">错误: {batch.error_message}</span>
                      )}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default BatchLogSection
