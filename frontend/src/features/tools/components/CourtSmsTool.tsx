import { useState } from 'react'
import { Search, Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { useCourtSmsList } from '../hooks/use-court-sms'

const STATUS_LABELS: Record<string, string> = {
  pending: '待处理', parsing: '解析中', downloading: '下载中',
  download_failed: '下载失败', matching: '匹配中', pending_manual: '待人工处理',
  renaming: '重命名中', notifying: '通知中', completed: '已完成', failed: '处理失败',
}

const STATUS_BADGE_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  completed: 'default', pending_manual: 'secondary', download_failed: 'destructive', failed: 'destructive',
}

const STATUS_FILTERS = ['all', 'completed', 'pending_manual', 'download_failed', 'failed'] as const

export function CourtSmsTool() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data, isLoading } = useCourtSmsList({
    status: statusFilter === 'all' ? undefined : statusFilter,
  })
  const items = data?.items ?? []

  const filtered = search
    ? items.filter((sms) =>
        sms.content.toLowerCase().includes(search.toLowerCase()) ||
        (sms.case_name && sms.case_name.toLowerCase().includes(search.toLowerCase()))
      )
    : items

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">法院短信</h1>
          <p className="text-muted-foreground text-sm mt-1">自动解析法院送达短信，关联案件并下载文书</p>
        </div>
        <Button size="sm"><Plus className="mr-1.5 size-4" />提交短信</Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="text-muted-foreground absolute left-3 top-1/2 size-4 -translate-y-1/2" />
          <Input type="text" placeholder="搜索内容或案件名称..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        {STATUS_FILTERS.map((s) => (
          <Button key={s} variant={s === statusFilter ? 'default' : 'outline'} size="sm" onClick={() => setStatusFilter(s)} className="h-8 text-xs">
            {s === 'all' ? '全部' : STATUS_LABELS[s] ?? s}
          </Button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[60px]">ID</TableHead>
              <TableHead className="w-[90px]">状态</TableHead>
              <TableHead>短信内容</TableHead>
              <TableHead className="w-[160px]">关联案件</TableHead>
              <TableHead className="w-[60px]">文书</TableHead>
              <TableHead className="w-[120px]">收到时间</TableHead>
              <TableHead className="w-[70px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}><div className="bg-muted h-4 w-20 animate-pulse rounded" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-muted-foreground text-sm">没有短信记录</TableCell>
              </TableRow>
            ) : filtered.map((sms) => {
              const statusLabel = STATUS_LABELS[sms.status] ?? sms.status
              const variant = STATUS_BADGE_VARIANT[sms.status] ?? 'outline'

              return (
                <TableRow key={sms.id}>
                  <TableCell className="text-muted-foreground text-sm">{sms.id}</TableCell>
                  <TableCell><Badge variant={variant} className="text-xs">{statusLabel}</Badge></TableCell>
                  <TableCell className="text-sm max-w-[400px] truncate" title={sms.content}>{sms.content}</TableCell>
                  <TableCell className="text-sm truncate max-w-[160px]" title={sms.case_name ?? undefined}>{sms.case_name || '-'}</TableCell>
                  <TableCell className="text-sm">{sms.has_documents ? <span className="text-status-green">有</span> : '-'}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">{sms.received_at ? new Date(sms.received_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}</TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" className="h-7 text-xs">
                      {sms.status === 'pending_manual' ? '关联' : '查看'}
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
