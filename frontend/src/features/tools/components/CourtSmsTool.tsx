import { useState, useMemo } from 'react'
import { Search, Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'

// TODO: Replace with real API data
const MOCK_DATA = [
  { id: 1, content: '【深圳中院】您有一份新的送达文书待查收，案号：（2024）粤03民初1234号，请登录人民法院在线服务网查看。', received_at: '2024-06-12 09:30', status: 'completed', case_numbers: ['（2024）粤03民初1234号'], case_name: '张三诉李四民间借贷纠纷', download_links: 2, notified: true },
  { id: 2, content: '【深圳中院】您代理的案件（2024）粤03民初5678号已立案，请关注后续进展。', received_at: '2024-06-11 14:20', status: 'completed', case_numbers: ['（2024）粤03民初5678号'], case_name: '王五诉赵六合同纠纷', download_links: 0, notified: true },
  { id: 3, content: '【人民法院在线服务网】您有一份新文书待送达，案号（2024）粤03民初9999号，请点击链接查收。', received_at: '2024-06-12 16:00', status: 'pending_manual', case_numbers: ['（2024）粤03民初9999号'], case_name: null, download_links: 1, notified: false },
  { id: 4, content: '【12368】您代理的（2024）粤03民初1234号案件定于2024年7月15日9时30分开庭。', received_at: '2024-06-10 10:00', status: 'completed', case_numbers: ['（2024）粤03民初1234号'], case_name: '张三诉李四民间借贷纠纷', download_links: 0, notified: true },
  { id: 5, content: '【湖北电子送达】案号（2024）鄂01民初888号，文书送达失败，请重新确认送达地址。', received_at: '2024-06-09 11:30', status: 'download_failed', case_numbers: ['（2024）鄂01民初888号'], case_name: null, download_links: 1, notified: false },
]

const STATUS_LABELS: Record<string, string> = {
  pending: '待处理', parsing: '解析中', downloading: '下载中',
  download_failed: '下载失败', matching: '匹配中', pending_manual: '待人工处理',
  renaming: '重命名中', notifying: '通知中', completed: '已完成', failed: '处理失败',
}

const STATUS_BADGE_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  completed: 'default', pending_manual: 'secondary', download_failed: 'destructive',
}

const STATUS_FILTERS = ['all', 'completed', 'pending_manual', 'failed'] as const

export function CourtSmsTool() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filtered = useMemo(() => {
    return MOCK_DATA.filter((sms) => {
      if (search && !sms.content.toLowerCase().includes(search.toLowerCase()) && !sms.case_numbers.join(' ').toLowerCase().includes(search.toLowerCase())) return false
      if (statusFilter !== 'all' && sms.status !== statusFilter) return false
      return true
    })
  }, [search, statusFilter])

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
          <Input type="text" placeholder="搜索内容或案号..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        {STATUS_FILTERS.map((s) => (
          <Button key={s} variant={s === statusFilter ? 'default' : 'outline'} size="sm" onClick={() => setStatusFilter(s)} className="h-8 text-xs">
            {s === 'all' ? '全部' : STATUS_LABELS[s] ?? s}
          </Button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-md border">
        <Table className="min-w-[700px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">ID</TableHead>
              <TableHead className="w-[90px]">状态</TableHead>
              <TableHead>短信内容</TableHead>
              <TableHead className="w-[150px]">关联案件</TableHead>
              <TableHead className="w-[140px]">案号</TableHead>
              <TableHead className="w-[60px]">文书</TableHead>
              <TableHead className="w-[50px]">通知</TableHead>
              <TableHead className="w-[110px]">收到时间</TableHead>
              <TableHead className="w-[60px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="h-32 text-center text-muted-foreground text-sm">没有匹配的短信记录</TableCell>
              </TableRow>
            ) : filtered.map((sms) => {
              const statusLabel = STATUS_LABELS[sms.status] ?? sms.status
              const variant = STATUS_BADGE_VARIANT[sms.status] ?? 'outline'
              const preview = sms.content.length > 55 ? sms.content.slice(0, 55) + '...' : sms.content

              return (
                <TableRow key={sms.id}>
                  <TableCell className="text-muted-foreground text-sm">{sms.id}</TableCell>
                  <TableCell><Badge variant={variant} className="text-xs">{statusLabel}</Badge></TableCell>
                  <TableCell className="text-sm max-w-[300px]" title={sms.content}>{preview}</TableCell>
                  <TableCell className="text-sm">{sms.case_name || '-'}</TableCell>
                  <TableCell className="text-sm">{sms.case_numbers[0] || '-'}</TableCell>
                  <TableCell className="text-sm">{sms.download_links > 0 ? `${sms.download_links} 个` : '-'}</TableCell>
                  <TableCell className="text-center">
                    {sms.notified
                      ? <span className="text-status-green text-sm">✓</span>
                      : <span className="text-muted-foreground text-sm">-</span>}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">{sms.received_at}</TableCell>
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
