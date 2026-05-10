import { useState } from 'react'
import { Download, Loader2, FileText, FileCheck } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { caseApi } from '../api'
import type { CaseParty } from '../types'
import { LEGAL_STATUS_LABELS } from '../types'

interface Props {
  caseId: number
  caseName: string
  parties: CaseParty[]
}

type DownloadKey = 'package' | 'letter' | 'legal-rep' | 'poa'

export function AuthorizationMaterialsSection({ caseId, caseName, parties }: Props) {
  const [loading, setLoading] = useState<DownloadKey | null>(null)
  const [legalRepDialog, setLegalRepDialog] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  const ourParties = parties.filter(p => p.client_detail?.is_our_client)

  const run = async (key: DownloadKey, fn: () => Promise<void>) => {
    setLoading(key)
    try {
      await fn()
      toast.success('下载成功')
    } catch {
      toast.error('下载失败')
    } finally {
      setLoading(null)
    }
  }

  const handleLegalRepConfirm = () => {
    if (selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    run('legal-rep', async () => {
      for (const id of ids) {
        const party = ourParties.find(p => p.client === id)
        await caseApi.downloadLegalRepCertificate(caseId, id, party?.client_detail?.name)
      }
    })
    setLegalRepDialog(false)
  }

  const toggleId = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelectedIds(prev =>
      prev.size === ourParties.length ? new Set() : new Set(ourParties.map(p => p.client))
    )
  }

  return (
    <>
      <div className="flex flex-wrap gap-1.5">
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={loading !== null || ourParties.length === 0}
          title={ourParties.length === 0 ? '没有我方当事人' : undefined}
          onClick={() => run('package', () => caseApi.downloadAuthorizationPackage(caseId, caseName))}
        >
          {loading === 'package' ? <Loader2 className="size-3 mr-1 animate-spin" /> : <Download className="size-3 mr-1" />}
          全套委托材料
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={loading !== null || ourParties.length === 0}
          title={ourParties.length === 0 ? '没有我方当事人' : undefined}
          onClick={() => { setSelectedIds(new Set()); setLegalRepDialog(true) }}
        >
          <FileCheck className="size-3 mr-1" />
          法定代表人证明
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={loading !== null}
          onClick={() => run('letter', () => caseApi.downloadAuthorizationLetter(caseId, caseName))}
        >
          {loading === 'letter' ? <Loader2 className="size-3 mr-1 animate-spin" /> : <FileText className="size-3 mr-1" />}
          所函
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={loading !== null || ourParties.length === 0}
          title={ourParties.length === 0 ? '没有我方当事人' : undefined}
          onClick={() => run('poa', () => caseApi.downloadCombinedPOA(caseId, caseName, ourParties.map(p => p.client)))}
        >
          {loading === 'poa' ? <Loader2 className="size-3 mr-1 animate-spin" /> : <FileText className="size-3 mr-1" />}
          授权委托书
        </Button>
      </div>

      {/* 法定代表人证明 — 选择当事人 */}
      <Dialog open={legalRepDialog} onOpenChange={(open) => { if (!open) setLegalRepDialog(false) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>法定代表人证明 — 选择当事人</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            {ourParties.length > 1 && (
              <label className="flex items-center gap-2 cursor-pointer text-xs text-muted-foreground pb-1 border-b border-border/40">
                <Checkbox
                  checked={selectedIds.size === ourParties.length}
                  onCheckedChange={toggleAll}
                />
                全选
              </label>
            )}
            {ourParties.map(p => (
              <label key={p.client} className="flex items-center gap-2 cursor-pointer text-sm">
                <Checkbox
                  checked={selectedIds.has(p.client)}
                  onCheckedChange={() => toggleId(p.client)}
                />
                <span>{p.client_detail?.name ?? `#${p.client}`}</span>
                {p.legal_status && (
                  <span className="text-xs text-muted-foreground">
                    （{LEGAL_STATUS_LABELS[p.legal_status as keyof typeof LEGAL_STATUS_LABELS]?.zh ?? p.legal_status}）
                  </span>
                )}
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLegalRepDialog(false)}>取消</Button>
            <Button
              onClick={handleLegalRepConfirm}
              disabled={selectedIds.size === 0 || loading !== null}
            >
              {loading !== null && <Loader2 className="mr-1 size-3 animate-spin" />}
              <Download className="mr-1 size-3" />
              生成并下载
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
