import { useState, useEffect, useCallback } from 'react'
import { caseApi } from '../api'
import type { PaymentRecord, PaymentRecordCategory, PaymentSummary } from '../types'

interface PaymentSectionProps {
  caseId: number
}

export function PaymentSection({ caseId }: PaymentSectionProps) {
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [summary, setSummary] = useState<PaymentSummary | null>(null)
  const [categories, setCategories] = useState<PaymentRecordCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingRecord, setEditingRecord] = useState<PaymentRecord | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    category_id: 0,
    amount: '',
    record_date: new Date().toISOString().split('T')[0],
    is_income: true,
    payment_method: '',
    payer_payee_name: '',
    description: '',
  })

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [paymentsRes, summaryRes, categoriesRes] = await Promise.all([
        caseApi.listCasePayments(caseId),
        caseApi.getPaymentSummary(caseId),
        caseApi.listPaymentCategories(),
      ])
      setPayments(paymentsRes)
      setSummary(summaryRes)
      setCategories(categoriesRes)
    } catch (err) {
      setError('加载数据失败')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError(null)
      if (editingRecord) {
        await caseApi.updatePayment(editingRecord.id, {
          ...formData,
          category_id: Number(formData.category_id),
          amount: Number(formData.amount),
        })
      } else {
        await caseApi.createPayment({
          ...formData,
          case_id: caseId,
          category_id: Number(formData.category_id),
          amount: Number(formData.amount),
        })
      }
      setShowForm(false)
      setEditingRecord(null)
      resetForm()
      loadData()
    } catch (err) {
      setError(editingRecord ? '更新失败' : '创建失败')
      console.error(err)
    }
  }

  const handleEdit = (record: PaymentRecord) => {
    setEditingRecord(record)
    setFormData({
      category_id: record.category,
      amount: String(record.amount),
      record_date: record.record_date,
      is_income: record.is_income,
      payment_method: record.payment_method || '',
      payer_payee_name: record.payer_payee_name || '',
      description: record.description || '',
    })
    setShowForm(true)
  }

  const handleDelete = async (recordId: number) => {
    if (!confirm('确定要删除这条记录吗？')) return
    try {
      await caseApi.deletePayment(recordId)
      loadData()
    } catch (err) {
      setError('删除失败')
      console.error(err)
    }
  }

  const resetForm = () => {
    setFormData({
      category_id: categories.find(c => c.is_income)?.id || 0,
      amount: '',
      record_date: new Date().toISOString().split('T')[0],
      is_income: true,
      payment_method: '',
      payer_payee_name: '',
      description: '',
    })
  }

  const incomeCategories = categories.filter(c => c.is_income)
  const expenseCategories = categories.filter(c => !c.is_income)

  if (loading) {
    return <div className="p-4 text-gray-500">加载中...</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">收支记录</h3>
        <button
          onClick={() => {
            resetForm()
            setEditingRecord(null)
            setShowForm(!showForm)
          }}
          className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          {showForm ? '取消' : '+ 添加记录'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded">
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="p-4 bg-gray-50 rounded-lg space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">类型</label>
              <div className="mt-1 flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={formData.is_income}
                    onChange={() => setFormData({ ...formData, is_income: true })}
                    className="mr-1"
                  />
                  收入
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={!formData.is_income}
                    onChange={() => setFormData({ ...formData, is_income: false })}
                    className="mr-1"
                  />
                  支出
                </label>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">金额</label>
              <input
                type="number"
                step="0.01"
                value={formData.amount}
                onChange={e => setFormData({ ...formData, amount: e.target.value })}
                className="mt-1 block w-full rounded border-gray-300 border px-3 py-1"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">款项用途</label>
              <select
                value={formData.category_id}
                onChange={e => setFormData({ ...formData, category_id: Number(e.target.value) })}
                className="mt-1 block w-full rounded border-gray-300 border px-3 py-1"
                required
              >
                <option value={0}>请选择</option>
                {formData.is_income ? (
                  incomeCategories.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))
                ) : (
                  expenseCategories.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))
                )}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">发生日期</label>
              <input
                type="date"
                value={formData.record_date}
                onChange={e => setFormData({ ...formData, record_date: e.target.value })}
                className="mt-1 block w-full rounded border-gray-300 border px-3 py-1"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {formData.is_income ? '付款方' : '收款方'}
              </label>
              <input
                type="text"
                value={formData.payer_payee_name}
                onChange={e => setFormData({ ...formData, payer_payee_name: e.target.value })}
                className="mt-1 block w-full rounded border-gray-300 border px-3 py-1"
                placeholder={formData.is_income ? '输入付款方名称' : '输入收款方名称'}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">支付方式</label>
              <select
                value={formData.payment_method || ''}
                onChange={e => setFormData({ ...formData, payment_method: e.target.value })}
                className="mt-1 block w-full rounded border-gray-300 border px-3 py-1"
              >
                <option value="">请选择</option>
                <option value="bank_transfer">银行转账</option>
                <option value="court_enforcement">法院执行</option>
                <option value="cash">现金</option>
                <option value="online_payment">线上支付</option>
                <option value="check">支票</option>
                <option value="other">其他</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">说明</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 block w-full rounded border-gray-300 border px-3 py-1"
              rows={2}
              placeholder="添加说明或备注"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                setEditingRecord(null)
              }}
              className="px-4 py-1 text-gray-600 border rounded hover:bg-gray-100"
            >
              取消
            </button>
            <button
              type="submit"
              className="px-4 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              {editingRecord ? '更新' : '创建'}
            </button>
          </div>
        </form>
      )}

      {summary && (
        <div className="grid grid-cols-3 gap-4 p-4 bg-blue-50 rounded-lg">
          <div className="text-center">
            <div className="text-sm text-gray-600">总收入</div>
            <div className="text-xl font-bold text-green-600">
              ¥{Number(summary.total_income).toLocaleString()}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600">总支出</div>
            <div className="text-xl font-bold text-red-600">
              ¥{Number(summary.total_expense).toLocaleString()}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-600">净收益</div>
            <div className={`text-xl font-bold ${Number(summary.net_amount) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ¥{Number(summary.net_amount).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h4 className="font-medium text-gray-700">收支明细</h4>
        {payments.length === 0 ? (
          <div className="text-center py-8 text-gray-500">暂无记录</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">日期</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">类型</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">用途</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">金额</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">对方</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {payments.map(record => (
                <tr key={record.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-sm">{record.record_date}</td>
                  <td className="px-3 py-2 text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs ${record.is_income ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {record.is_income ? '收入' : '支出'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-sm">{record.category_name || record.category}</td>
                  <td className={`px-3 py-2 text-sm text-right font-medium ${record.is_income ? 'text-green-600' : 'text-red-600'}`}>
                    {record.is_income ? '+' : '-'}¥{Number(record.amount).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-sm">{record.payer_payee_name || '-'}</td>
                  <td className="px-3 py-2 text-sm">
                    <button
                      onClick={() => handleEdit(record)}
                      className="text-blue-600 hover:text-blue-800 mr-2"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(record.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default PaymentSection
