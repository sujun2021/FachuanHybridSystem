import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Download, Search, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useCollectionContracts, useCaseDetails, getExportUrl } from '@/features/finance/api'
import {
  FEE_MODE_OPTIONS,
  EXPORT_FIELDS,
  type CollectionFilters,
  type ContractSummary,
  type ExportLevel,
} from '@/features/finance/types'

function formatMoney(v: number | null | undefined): string {
  if (v == null) return '风险收费'
  return `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatRate(r: number): string {
  return `${(r * 100).toFixed(1)}%`
}

// ==================== Export Dialog ====================
function ExportDialog({
  open,
  onClose,
  filters,
}: {
  open: boolean
  onClose: () => void
  filters: CollectionFilters
}) {
  const [level, setLevel] = useState<ExportLevel>('contract')

  if (!open) return null

  const url = getExportUrl({ ...filters, level })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <Card className="p-6 w-[420px] max-w-[90vw] space-y-4">
        <h3 className="text-lg font-semibold">导出配置</h3>

        <div>
          <label className="text-sm font-medium mb-2 block">导出层级</label>
          <div className="flex gap-2">
            {(['contract', 'case', 'detail'] as ExportLevel[]).map((l) => (
              <Button
                key={l}
                variant={level === l ? 'default' : 'outline'}
                size="sm"
                onClick={() => setLevel(l)}
              >
                {{ contract: '合同汇总', case: '案件明细', detail: '逐笔明细' }[l]}
              </Button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">导出字段</label>
          <div className="text-xs text-muted-foreground">
            {EXPORT_FIELDS[level].map((f) => f.label).join(' / ')}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <a href={url} download>
            <Button>
              <Download className="w-4 h-4 mr-1" />
              导出 .xlsx
            </Button>
          </a>
        </div>
      </Card>
    </div>
  )
}

// ==================== Main Page ====================
export default function CollectionPage() {
  const [filters, setFilters] = useState<CollectionFilters>({})
  const [expandedContract, setExpandedContract] = useState<number | null>(null)
  const [exportOpen, setExportOpen] = useState(false)

  const { data, isLoading } = useCollectionContracts({
    ...filters,
    page: 1,
    page_size: 100,
  })

  const { data: caseData } = useCaseDetails(expandedContract)

  const contracts = data?.contracts ?? []

  const handleFilterChange = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }))
    setExpandedContract(null)
  }, [])

  const resetFilters = useCallback(() => {
    setFilters({})
    setExpandedContract(null)
  }, [])

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold">客户收款看板</h1>
        <p className="text-muted-foreground text-sm mt-1">
          合同收款汇总 / 案件收款明细 / 收款记录查询
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="text-xs text-muted-foreground">合同应收</div>
          <div className="text-2xl font-bold text-blue-600">
            {formatMoney(data?.total_expected)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground">已收总额</div>
          <div className="text-2xl font-bold text-green-600">
            {formatMoney(data?.total_received)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground">未收余额</div>
          <div className="text-2xl font-bold text-red-600">
            {formatMoney(data?.total_balance)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground">回款率</div>
          <div className="text-2xl font-bold text-purple-600">
            {data?.overall_rate != null ? formatRate(data.overall_rate) : '--'}
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-muted-foreground mb-1 block">案件名称</label>
            <Input
              placeholder="输入案件名称搜索..."
              value={filters.case_name ?? ''}
              onChange={(e) => handleFilterChange('case_name', e.target.value)}
            />
          </div>
          <div className="w-[150px]">
            <label className="text-xs text-muted-foreground mb-1 block">收费模式</label>
            <Select
              value={filters.fee_mode ?? ''}
              onChange={(e) => handleFilterChange('fee_mode', e.target.value)}
            >
              {FEE_MODE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">开始日期</label>
            <Input
              type="date"
              value={filters.start_date ?? ''}
              onChange={(e) => handleFilterChange('start_date', e.target.value)}
              className="w-[160px]"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">结束日期</label>
            <Input
              type="date"
              value={filters.end_date ?? ''}
              onChange={(e) => handleFilterChange('end_date', e.target.value)}
              className="w-[160px]"
            />
          </div>
          <Button variant="outline" size="sm" onClick={resetFilters}>
            <RotateCcw className="w-4 h-4 mr-1" /> 重置
          </Button>
          <Button size="sm" onClick={() => setExportOpen(true)}>
            <Download className="w-4 h-4 mr-1" /> 导出 Excel
          </Button>
        </div>
      </Card>

      {/* Contract Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>合同名称</TableHead>
              <TableHead>客户</TableHead>
              <TableHead>收费模式</TableHead>
              <TableHead className="text-right">合同应收</TableHead>
              <TableHead className="text-right">已收金额</TableHead>
              <TableHead className="text-right">未收余额</TableHead>
              <TableHead className="text-right">回款率</TableHead>
              <TableHead className="text-center">案件数</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                  加载中...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && contracts.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                  暂无数据
                </TableCell>
              </TableRow>
            )}
            {contracts.map((c: ContractSummary) => (
              <>
                <TableRow
                  key={c.contract_id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() =>
                    setExpandedContract(
                      expandedContract === c.contract_id ? null : c.contract_id
                    )
                  }
                >
                  <TableCell>
                    <ChevronRight
                      className={`w-4 h-4 transition-transform ${
                        expandedContract === c.contract_id ? 'rotate-90' : ''
                      }`}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{c.contract_name}</TableCell>
                  <TableCell className="text-muted-foreground">{c.client_name}</TableCell>
                  <TableCell>{c.fee_mode_display}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.fixed_amount)}</TableCell>
                  <TableCell className="text-right text-green-600">
                    {formatMoney(c.total_received)}
                  </TableCell>
                  <TableCell className="text-right text-red-600">
                    {formatMoney(c.balance)}
                  </TableCell>
                  <TableCell className="text-right">{formatRate(c.received_rate)}</TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {c.case_count}
                  </TableCell>
                </TableRow>
                {/* Expanded Cases */}
                {expandedContract === c.contract_id && caseData && (
                  <>
                    <TableRow className="bg-muted/30">
                      <TableCell colSpan={9} className="p-0">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-8" />
                              <TableHead>案件名称</TableHead>
                              <TableHead>状态</TableHead>
                              <TableHead className="text-right">已收律师费</TableHead>
                              <TableHead className="text-right">总收入</TableHead>
                              <TableHead className="text-right">总支出</TableHead>
                              <TableHead className="text-right">净收入</TableHead>
                              <TableHead className="text-center">收款笔数</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {caseData.cases.map((cs) => (
                              <TableRow key={cs.case_id}>
                                <TableCell />
                                <TableCell className="text-sm">{cs.case_name}</TableCell>
                                <TableCell className="text-xs">{cs.case_status}</TableCell>
                                <TableCell className="text-right text-sm">
                                  {formatMoney(cs.attorney_fee_received)}
                                </TableCell>
                                <TableCell className="text-right text-sm text-green-600">
                                  {formatMoney(cs.case_income)}
                                </TableCell>
                                <TableCell className="text-right text-sm text-red-600">
                                  {formatMoney(cs.case_expense)}
                                </TableCell>
                                <TableCell className="text-right text-sm font-medium">
                                  {formatMoney(cs.net_income)}
                                </TableCell>
                                <TableCell className="text-center text-sm text-muted-foreground">
                                  {cs.payment_count}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableCell>
                    </TableRow>
                  </>
                )}
              </>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Export Dialog */}
      <ExportDialog open={exportOpen} onClose={() => setExportOpen(false)} filters={filters} />
    </div>
  )
}
