import { forwardRef, useImperativeHandle, useMemo, useState } from 'react'
import { Paperclip, Trash2, Loader2, Download, Bell, ChevronDown, ChevronRight, Plus, X, DollarSign } from 'lucide-react'
import { formatDate } from '@/lib/date'
import { resolveMediaUrl } from '@/lib/api'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

import { useLogMutations } from '../hooks/use-log-mutations'
import {
  type CaseLog,
  type PaymentRecordInput,
  CASE_LOG_REMINDER_TYPE_LABELS,
  PAYMENT_PURPOSE_LABELS,
  PAYMENT_DIRECTION,
  PAYMENT_METHOD_LABELS,
} from '../types'

export interface CaseLogSectionProps {
  logs: CaseLog[]
  editable?: boolean
  caseId?: number
}

export interface CaseLogSectionRef {
  openDialog: () => void
}

interface PaymentRow {
  direction: 'income' | 'expense'
  amount: string
  purpose: string
  payment_method: string
  date: string
  note: string
}

const DEFAULT_PAYMENT_ROW: PaymentRow = {
  direction: 'expense',
  amount: '',
  purpose: 'court_fee',
  payment_method: 'bank_transfer',
  date: new Date().toISOString().slice(0, 10),
  note: '',
}

function parsePaymentText(text: string): PaymentRow[] {
  if (!text.trim()) return []
  const results: PaymentRow[] = []
  const parts = text.split(/[、，；;]/)
  const today = new Date().toISOString().slice(0, 10)
  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue
    const amountMatch = trimmed.match(/(\d+(?:\.\d{1,2})?)\s*元?$/)
    if (!amountMatch) continue
    const amount = amountMatch[1]
    const namePart = trimmed.slice(0, amountMatch.index).trim()
    let direction: 'income' | 'expense' = 'expense'
    let purposeName = namePart
    if (/收入|回款|退还|和解/.test(namePart)) {
      direction = 'income'
    }
    if (/支付|支出|费用|费$/.test(namePart)) {
      direction = 'expense'
    }
    if (/支付|支出/.test(namePart)) {
      purposeName = namePart.replace(/^(支付|支出)/, '').trim()
    }
    let purposeKey = 'other_expense'
    const lower = purposeName.replace(/\s/g, '')
    for (const [key, label] of Object.entries(PAYMENT_PURPOSE_LABELS)) {
      if (label.replace(/\s/g, '') === lower) {
        purposeKey = key
        break
      }
    }
    if (purposeKey === 'other_expense' && direction === 'income') {
      if (/回款/.test(purposeName)) purposeKey = 'enforcement_recovery'
      else purposeKey = 'counterparty_payment'
    }
    results.push({
      direction,
      amount,
      purpose: purposeKey,
      payment_method: 'bank_transfer',
      date: today,
      note: '',
    })
  }
  return results
}

export const CaseLogSection = forwardRef<CaseLogSectionRef, CaseLogSectionProps>(function CaseLogSection(
  { logs, editable, caseId },
  ref,
) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newContent, setNewContent] = useState('')
  const [reminderType, setReminderType] = useState('')
  const [reminderTime, setReminderTime] = useState('')
  const [paymentExpanded, setPaymentExpanded] = useState(false)
  const [paymentRows, setPaymentRows] = useState<PaymentRow[]>([
    { ...DEFAULT_PAYMENT_ROW },
    { ...DEFAULT_PAYMENT_ROW },
  ])
  const [quickText, setQuickText] = useState('')

  const mutations = useLogMutations(caseId ?? 0)

  useImperativeHandle(ref, () => ({ openDialog: () => setDialogOpen(true) }), [])

  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [logs],
  )

  const resetForm = () => {
    setNewContent('')
    setReminderType('')
    setReminderTime('')
    setPaymentExpanded(false)
    setPaymentRows([{ ...DEFAULT_PAYMENT_ROW }, { ...DEFAULT_PAYMENT_ROW }])
    setQuickText('')
  }

  const handleQuickParse = () => {
    const parsed = parsePaymentText(quickText)
    if (parsed.length === 0) {
      toast.error('未能解析任何收支记录，格式示例：支付诉讼费5000、支付保全费600')
      return
    }
    setPaymentRows(parsed)
    setQuickText('')
    setPaymentExpanded(true)
    toast.success(`已解析 ${parsed.length} 条收支记录`)
  }

  const updatePaymentRow = (index: number, field: keyof PaymentRow, value: string) => {
    setPaymentRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }

  const removePaymentRow = (index: number) => {
    setPaymentRows((prev) => prev.filter((_, i) => i !== index))
  }

  const addPaymentRow = () => {
    setPaymentRows((prev) => [...prev, { ...DEFAULT_PAYMENT_ROW }])
  }

  const handleAdd = () => {
    if (!caseId || !newContent.trim()) return
    const hasReminder = reminderType && reminderTime
    const validPayments: PaymentRecordInput[] = paymentRows
      .filter((r) => r.amount && r.amount.trim())
      .map((r) => ({
        direction: r.direction,
        amount: r.amount.trim(),
        purpose: r.purpose,
        payment_method: r.payment_method,
        date: r.date,
        note: r.note,
      }))
    mutations.createLog.mutate(
      {
        case_id: caseId,
        content: newContent.trim(),
        ...(hasReminder ? { reminder_type: reminderType, reminder_time: reminderTime } : {}),
        ...(validPayments.length > 0 ? { payment_records: validPayments } : {}),
      },
      {
        onSuccess: () => {
          toast.success('添加日志成功')
          setDialogOpen(false)
          resetForm()
        },
        onError: (e) => toast.error(e.message || '添加失败'),
      },
    )
  }

  const handleDelete = (id: number) => {
    if (!mutations) return
    mutations.deleteLog.mutate(id, {
      onSuccess: () => toast.success('删除成功'),
      onError: (e) => toast.error(e.message || '删除失败'),
    })
  }

  return (
    <div className="space-y-3">
      {editable && caseId && (
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm() }}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>添加案件日志</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>日志内容</Label>
                <textarea
                  className="border-input bg-background placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 w-full rounded-md border px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px] min-h-[100px] resize-y"
                  placeholder="请输入日志内容"
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                />
              </div>

              {/* Payment records section */}
              <div className="border rounded-lg">
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/50 rounded-t-lg"
                  onClick={() => setPaymentExpanded(!paymentExpanded)}
                >
                  <span className="flex items-center gap-2">
                    <DollarSign className="size-4 text-muted-foreground" />
                    收支记录
                    {paymentRows.some((r) => r.amount.trim()) && (
                      <span className="text-xs text-primary font-normal">
                        ({paymentRows.filter((r) => r.amount.trim()).length} 条)
                      </span>
                    )}
                  </span>
                  {paymentExpanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                </button>
                {paymentExpanded && (
                  <div className="px-4 pb-4 space-y-3">
                    {/* Quick entry */}
                    <div className="flex gap-2">
                      <Input
                        placeholder="快速录入：支付诉讼费5000、保全费600"
                        value={quickText}
                        onChange={(e) => setQuickText(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleQuickParse() } }}
                        className="text-xs h-8"
                      />
                      <Button size="sm" variant="outline" onClick={handleQuickParse} type="button" className="shrink-0 h-8 text-xs">智能解析</Button>
                    </div>

                    {/* Manual rows */}
                    <div className="space-y-2">
                      <div className="grid grid-cols-12 gap-1 text-[11px] text-muted-foreground px-1">
                        <span className="col-span-2">方向</span>
                        <span className="col-span-3">用途</span>
                        <span className="col-span-2">金额</span>
                        <span className="col-span-3">方式</span>
                        <span className="col-span-1">日期</span>
                        <span className="col-span-1"></span>
                      </div>
                      {paymentRows.map((row, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <Select value={row.direction} onValueChange={(v) => updatePaymentRow(i, 'direction', v)}>
                            <SelectTrigger className="col-span-2 h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(PAYMENT_DIRECTION).map(([k, v]) => (
                                <SelectItem key={k} value={k}>{v}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Select value={row.purpose} onValueChange={(v) => updatePaymentRow(i, 'purpose', v)}>
                            <SelectTrigger className="flex-1 h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="max-h-60">
                              {Object.entries(PAYMENT_PURPOSE_LABELS).map(([k, v]) => (
                                <SelectItem key={k} value={k}>{v}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input
                            className="w-20 h-7 text-xs"
                            placeholder="金额"
                            value={row.amount}
                            onChange={(e) => updatePaymentRow(i, 'amount', e.target.value)}
                          />
                          <Select value={row.payment_method} onValueChange={(v) => updatePaymentRow(i, 'payment_method', v)}>
                            <SelectTrigger className="w-20 h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(PAYMENT_METHOD_LABELS).map(([k, v]) => (
                                <SelectItem key={k} value={k}>{v}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input
                            className="w-24 h-7 text-xs"
                            type="date"
                            value={row.date}
                            onChange={(e) => updatePaymentRow(i, 'date', e.target.value)}
                          />
                          <Button variant="ghost" size="icon-xs" className="size-6 shrink-0" onClick={() => removePaymentRow(i)} type="button">
                            <X className="size-3" />
                          </Button>
                        </div>
                      ))}
                      <Button variant="ghost" size="sm" onClick={addPaymentRow} type="button" className="text-xs h-7">
                        <Plus className="size-3 mr-1" /> 添加行
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t pt-4">
                <p className="text-xs font-medium text-muted-foreground mb-3">提醒设置（可选）</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label className="text-xs">提醒类型</Label>
                    <Select value={reminderType} onValueChange={setReminderType}>
                      <SelectTrigger>
                        <SelectValue placeholder="不设置提醒" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(CASE_LOG_REMINDER_TYPE_LABELS).map(([key, label]) => (
                          <SelectItem key={key} value={key}>{label.zh}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">提醒时间</Label>
                    <Input
                      type="datetime-local"
                      value={reminderTime}
                      onChange={(e) => setReminderTime(e.target.value)}
                      disabled={!reminderType}
                    />
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setDialogOpen(false); resetForm() }}>取消</Button>
              <Button
                onClick={handleAdd}
                disabled={!newContent.trim() || (reminderType && !reminderTime) || mutations?.createLog.isPending}
              >
                {mutations?.createLog.isPending && <Loader2 className="mr-1 size-3 animate-spin" />}
                确认
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {sortedLogs.length === 0 ? (
        <p className="text-muted-foreground text-xs">暂无案件日志</p>
      ) : (
        <div className="relative">
          <div className="absolute left-[5px] top-2 bottom-2 w-px bg-border" />
          <div className="space-y-0">
            {sortedLogs.map((log, index) => {
              const actorName = log.actor_detail?.real_name || log.actor_detail?.username || '未知'
              const attachCount = log.attachments?.length ?? 0
              const reminderCount = log.reminders?.length ?? 0
              const paymentCount = log.payment_records?.length ?? 0

              return (
                <div key={log.id} className="group relative pl-7 pb-3 last:pb-0">
                  <div className={`absolute left-0 top-[5px] size-[11px] rounded-full border-2 bg-background ${
                    index === 0 ? 'border-primary' : 'border-border'
                  }`}>
                    {index === 0 && <div className="absolute inset-[2px] rounded-full bg-primary" />}
                  </div>

                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-foreground">{actorName}</span>
                    <span className="text-xs text-muted-foreground">{formatDate(log.created_at)}</span>
                    {editable && caseId && (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon-xs" className="size-5 ml-auto opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive">
                            <Trash2 className="size-3" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent size="sm">
                          <AlertDialogHeader>
                            <AlertDialogTitle>确认删除</AlertDialogTitle>
                            <AlertDialogDescription>确定要删除这条日志吗？</AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>取消</AlertDialogCancel>
                            <AlertDialogAction variant="destructive" onClick={() => handleDelete(log.id)}>删除</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                  </div>

                  <p className="text-[13px] leading-snug whitespace-pre-wrap text-foreground">{log.content}</p>

                  {/* Payment badges */}
                  {paymentCount > 0 && (
                    <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                      {log.payment_records?.map((pr) => (
                        <span
                          key={pr.id}
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] ${
                            pr.direction === 'income'
                              ? 'border-green-200 bg-green-50 text-green-700'
                              : 'border-red-200 bg-red-50 text-red-700'
                          }`}
                        >
                          <DollarSign className="size-3" />
                          {pr.direction_label} ¥{pr.amount} {pr.purpose_label}
                        </span>
                      ))}
                    </div>
                  )}

                  {reminderCount > 0 && (
                    <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                      {log.reminders?.map((r) => (
                        <span key={r.id} className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                          <Bell className="size-3" />
                          {CASE_LOG_REMINDER_TYPE_LABELS[r.reminder_type as keyof typeof CASE_LOG_REMINDER_TYPE_LABELS]?.zh ?? r.reminder_type}
                          <span className="text-amber-600 ml-0.5">{formatDate(r.due_at)}</span>
                          {r.is_completed && <span className="text-green-600 ml-0.5">✓</span>}
                        </span>
                      ))}
                    </div>
                  )}

                  {attachCount > 0 && (
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      <Paperclip className="size-3 text-muted-foreground shrink-0" />
                      {log.attachments?.map((att) => {
                        const url = att.media_url || att.file_path
                        const displayName = att.original_filename || `附件 #${att.id}`
                        return url ? (
                          <a
                            key={att.id}
                            href={resolveMediaUrl(url) ?? url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                          >
                            <Download className="size-3" />
                            {displayName}
                          </a>
                        ) : (
                          <span key={att.id} className="text-xs text-muted-foreground">{displayName}</span>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
})

export default CaseLogSection
