import { Link } from 'react-router'
import { Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function PendingApproval() {
  return (
    <div className="text-center space-y-4">
      <div className="flex justify-center">
        <Clock className="h-16 w-16 text-muted-foreground" />
      </div>
      <h2 className="text-xl font-semibold">注册成功</h2>
      <p className="text-muted-foreground">
        您的账号正在等待管理员审批，审批通过后即可登录使用。
      </p>
      <Button asChild variant="outline">
        <Link to="/login">返回登录</Link>
      </Button>
    </div>
  )
}
