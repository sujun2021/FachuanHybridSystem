import { Landmark } from 'lucide-react'

import type { SupervisingAuthority } from '../types'

export interface AuthoritySectionProps {
  authorities: SupervisingAuthority[]
  editable?: boolean
  caseId?: number
}

export function AuthoritySection({ authorities }: AuthoritySectionProps) {
  if (authorities.length === 0) {
    return <p className="text-muted-foreground text-xs">暂无主管机关</p>
  }

  return (
    <div className="divide-y divide-border/40">
      {authorities.map((auth) => (
        <div key={auth.id} className="flex items-center gap-2 py-1.5">
          <Landmark className="text-muted-foreground size-3.5 shrink-0" />
          <span className="text-[13px] font-medium">{auth.name || '未命名机关'}</span>
          {auth.authority_type_display && (
            <span className="text-[11px] text-muted-foreground">({auth.authority_type_display})</span>
          )}
        </div>
      ))}
    </div>
  )
}

export default AuthoritySection
