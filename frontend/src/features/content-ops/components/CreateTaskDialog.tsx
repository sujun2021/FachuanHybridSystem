import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, Search, FileText } from 'lucide-react'
import { useCreateTask } from '../hooks/use-content-ops'
import { VOICE_OPTIONS } from '../types'
import type { TaskMode } from '../types'
import { useCredentials } from '@/features/organization/hooks/use-credentials'
import { toast } from 'sonner'

interface CreateTaskDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultMode?: TaskMode
  defaultKeyword?: string
  defaultCaseSummary?: string
}

export function CreateTaskDialog({
  open,
  onOpenChange,
  defaultMode = 'direct',
  defaultKeyword = '',
  defaultCaseSummary = '',
}: CreateTaskDialogProps) {
  const [mode, setMode] = useState<TaskMode>(defaultMode)
  const [keyword, setKeyword] = useState(defaultKeyword)
  const [caseSummary, setCaseSummary] = useState(defaultCaseSummary)
  const [directContent, setDirectContent] = useState('')
  const [voice, setVoice] = useState('冰糖')
  const [credentialId, setCredentialId] = useState<number | null>(null)

  // Sync props when dialog opens
  useEffect(() => {
    if (open) {
      setMode(defaultMode)
      setKeyword(defaultKeyword)
      setCaseSummary(defaultCaseSummary)
    }
  }, [open, defaultMode, defaultKeyword, defaultCaseSummary])

  const createTask = useCreateTask()
  const { data: credentials = [] } = useCredentials()

  // 过滤威科先行相关凭证
  const weikeCredentials = credentials.filter((c) => {
    const name = c.site_name.toLowerCase()
    return name.includes('wk') || name.includes('weike') || name.includes('wkinfo')
  })

  const handleSubmit = () => {
    if (mode === 'search') {
      if (!keyword.trim()) {
        toast.error('请输入检索关键词')
        return
      }
      if (!credentialId) {
        toast.error('请选择法律检索账号')
        return
      }
    }
    if (mode === 'direct' && !directContent.trim()) {
      toast.error('请输入内容')
      return
    }

    createTask.mutate(
      {
        mode,
        keyword: mode === 'search' ? keyword : undefined,
        credential_id: mode === 'search' ? credentialId : undefined,
        case_summary: caseSummary || undefined,
        direct_content: mode === 'direct' ? directContent : undefined,
        voice,
      },
      {
        onSuccess: (task) => {
          toast.success(`任务 #${task.id} 已创建，正在处理中`)
          onOpenChange(false)
          resetForm()
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : '创建任务失败')
        },
      },
    )
  }

  const resetForm = () => {
    setKeyword('')
    setCaseSummary('')
    setDirectContent('')
    setVoice('冰糖')
    setCredentialId(null)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>创建内容任务</DialogTitle>
          <DialogDescription>
            {mode === 'search'
              ? 'AI 将通过关键词检索法律案例，然后生成叙事文章和音频'
              : 'AI 将把你的内容改写为叙事风格的文章并生成音频'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 模式切换 */}
          <div className="flex gap-2">
            <Button
              type="button"
              variant={mode === 'search' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setMode('search')}
            >
              <Search className="w-4 h-4 mr-1" />
              检索模式
            </Button>
            <Button
              type="button"
              variant={mode === 'direct' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setMode('direct')}
            >
              <FileText className="w-4 h-4 mr-1" />
              直投模式
            </Button>
          </div>

          {/* 检索模式字段 */}
          {mode === 'search' && (
            <>
              <div className="space-y-2">
                <Label>检索关键词 *</Label>
                <Input
                  placeholder="输入法律案例关键词，如：邻里纠纷、劳动仲裁"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>法律检索账号 *</Label>
                {weikeCredentials.length === 0 ? (
                  <p className="text-xs text-destructive">
                    未找到威科先行相关账号，请先在「组织管理 - 凭证管理」中添加
                  </p>
                ) : (
                  <Select
                    value={credentialId?.toString() ?? ''}
                    onValueChange={(v) => setCredentialId(Number(v))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择检索账号" />
                    </SelectTrigger>
                    <SelectContent>
                      {weikeCredentials.map((c) => (
                        <SelectItem key={c.id} value={c.id.toString()}>
                          {c.site_name} - {c.account}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </>
          )}

          {/* 直投模式字段 */}
          {mode === 'direct' && (
            <div className="space-y-2">
              <Label>输入内容 *</Label>
              <Textarea
                placeholder="粘贴案例内容、判决书摘要或任何法律文本..."
                value={directContent}
                onChange={(e) => setDirectContent(e.target.value)}
                rows={6}
              />
            </div>
          )}

          {/* 通用字段 */}
          <div className="space-y-2">
            <Label>案例摘要 <span className="text-muted-foreground">(可选)</span></Label>
            <Input
              placeholder="简要描述案例背景，帮助 AI 更好理解"
              value={caseSummary}
              onChange={(e) => setCaseSummary(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>语音音色</Label>
            <Select value={voice} onValueChange={setVoice}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VOICE_OPTIONS.map((v) => (
                  <SelectItem key={v.value} value={v.value}>
                    {v.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={createTask.isPending}>
            {createTask.isPending && <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />}
            创建任务
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
