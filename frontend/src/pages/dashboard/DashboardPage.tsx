import { useDashboardStats } from '@/features/dashboard'
import { StatsCards } from '@/features/dashboard/components/StatsCards'
import { TrendChart } from '@/features/dashboard/components/TrendChart'
import { CaseDistributionChart } from '@/features/dashboard/components/CaseDistributionChart'
import { CalendarCard } from '@/features/dashboard/components/CalendarCard'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Calculator, MessageSquare, Truck, ArrowRightLeft, LayoutDashboard } from 'lucide-react'

const TOOLS = [
  { label: '法院短信', icon: MessageSquare, href: '/admin/tools/court-sms' },
  { label: 'LPR 计算器', icon: Calculator, href: '/admin/tools/lpr-calculator' },
  { label: '快递查询', icon: Truck, href: '/admin/tools/courier-tracking' },
  { label: '要素转换', icon: ArrowRightLeft, href: '/admin/tools/element-convert' },
  { label: 'Django Admin', icon: LayoutDashboard, href: '/admin/' },
]

export default function DashboardPage() {
  const { data, isLoading } = useDashboardStats()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">仪表盘</h1>
        <p className="text-muted-foreground text-sm mt-1">欢迎回来。以下是今日概览。</p>
      </div>

      <StatsCards data={data} isLoading={isLoading} />

      <Card className="p-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-muted-foreground shrink-0">快捷工具:</span>
          {TOOLS.map((t) => (
            <Button key={t.href} variant="outline" size="sm" className="h-7 text-xs gap-1" asChild>
              <a href={t.href}>
                <t.icon className="size-3" />
                {t.label}
              </a>
            </Button>
          ))}
        </div>
      </Card>

      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        <TrendChart data={data} isLoading={isLoading} />
        <CaseDistributionChart data={data} isLoading={isLoading} />
      </div>

      <CalendarCard />
    </div>
  )
}
