import { useEffect, useCallback, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, Save, X } from 'lucide-react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

import { useCredentials } from '@/features/organization/hooks/use-credentials'
import { messageSourceApi } from '../api'
import { SOURCE_TYPE_LABELS, type SourceType, type MessageSource } from '../types'

interface MessageSourceFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  source?: MessageSource | null
}

const createSchema = z.object({
  display_name: z.string().min(1, '显示名称不能为空'),
  source_type: z.string().min(1, '请选择来源类型'),
  credential_id: z.number({ message: '请选择关联凭证' }).min(1, '请选择关联凭证'),
  poll_interval_minutes: z.number().int().min(1, '至少 1 分钟').max(1440, '最多 1440 分钟'),
  is_enabled: z.boolean(),
})

const editSchema = z.object({
  display_name: z.string().min(1, '显示名称不能为空'),
  poll_interval_minutes: z.number().int().min(1, '至少 1 分钟').max(1440, '最多 1440 分钟'),
  is_enabled: z.boolean(),
})


export function MessageSourceFormDialog({ open, onOpenChange, source }: MessageSourceFormDialogProps) {
  const isEditMode = !!source
  const queryClient = useQueryClient()
  const { data: credentials = [], isLoading: isLoadingCredentials } = useCredentials()
  const [isPending, setIsPending] = useState(false)

  const createForm = useForm({
    resolver: zodResolver(createSchema),
    defaultValues: { display_name: '', source_type: 'imap', credential_id: undefined as unknown as number, poll_interval_minutes: 30, is_enabled: true },
  })

  const editForm = useForm({
    resolver: zodResolver(editSchema),
    defaultValues: { display_name: '', poll_interval_minutes: 30, is_enabled: true },
  })

  useEffect(() => {
    if (!open) return
    if (isEditMode && source) {
      editForm.reset({
        display_name: source.display_name,
        poll_interval_minutes: source.poll_interval_minutes,
        is_enabled: source.is_enabled,
      })
    } else {
      createForm.reset({
        display_name: '',
        source_type: 'imap',
        credential_id: undefined as unknown as number,
        poll_interval_minutes: 30,
        is_enabled: true,
      })
    }
  }, [open, isEditMode, source, createForm, editForm])

  const handleCreate = useCallback(async (data: Record<string, unknown>) => {
    setIsPending(true)
    try {
      await messageSourceApi.create({
        display_name: data.display_name as string,
        source_type: data.source_type as string,
        credential_id: data.credential_id as number,
        poll_interval_minutes: data.poll_interval_minutes as number,
        is_enabled: data.is_enabled as boolean,
      })
      toast.success('消息来源创建成功')
      queryClient.invalidateQueries({ queryKey: ['message-sources'] })
      onOpenChange(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '创建失败，请重试')
    } finally {
      setIsPending(false)
    }
  }, [queryClient, onOpenChange])

  const handleEdit = useCallback(async (data: Record<string, unknown>) => {
    if (!source) return
    setIsPending(true)
    try {
      await messageSourceApi.update(source.id, {
        display_name: data.display_name as string,
        poll_interval_minutes: data.poll_interval_minutes as number,
        is_enabled: data.is_enabled as boolean,
      })
      toast.success('消息来源更新成功')
      queryClient.invalidateQueries({ queryKey: ['message-sources'] })
      onOpenChange(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '更新失败，请重试')
    } finally {
      setIsPending(false)
    }
  }, [source, queryClient, onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditMode ? '编辑消息来源' : '添加消息来源'}</DialogTitle>
          <DialogDescription>
            {isEditMode ? '修改消息来源配置' : '配置新的消息同步来源'}
          </DialogDescription>
        </DialogHeader>

        {isEditMode ? (
          <Form {...editForm}>
            <form onSubmit={editForm.handleSubmit(handleEdit)} className="space-y-4">
              <FormField control={editForm.control} name="display_name" render={({ field }) => (
                <FormItem>
                  <FormLabel>显示名称 <span className="text-destructive">*</span></FormLabel>
                  <FormControl>
                    <Input placeholder="例：法院邮件" disabled={isPending} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />

              <div className="space-y-1.5">
                <FormLabel>来源类型</FormLabel>
                <Input value={SOURCE_TYPE_LABELS[source?.source_type as SourceType] ?? source?.source_type} disabled />
              </div>

              <div className="space-y-1.5">
                <FormLabel>关联凭证</FormLabel>
                <Input value={source?.credential_account ?? ''} disabled />
              </div>

              <FormField control={editForm.control} name="poll_interval_minutes" render={({ field }) => (
                <FormItem>
                  <FormLabel>轮询间隔（分钟）</FormLabel>
                  <FormControl>
                    <Input type="number" min={1} max={1440} disabled={isPending} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />

              <FormField control={editForm.control} name="is_enabled" render={({ field }) => (
                <FormItem className="flex items-center gap-3">
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} disabled={isPending} />
                  </FormControl>
                  <FormLabel className="!mt-0">启用</FormLabel>
                </FormItem>
              )} />

              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
                  <X className="mr-1.5 size-4" />取消
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? <><Loader2 className="mr-1.5 size-4 animate-spin" />保存中...</> : <><Save className="mr-1.5 size-4" />保存</>}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        ) : (
          <Form {...createForm}>
            <form onSubmit={createForm.handleSubmit(handleCreate)} className="space-y-4">
              <FormField control={createForm.control} name="display_name" render={({ field }) => (
                <FormItem>
                  <FormLabel>显示名称 <span className="text-destructive">*</span></FormLabel>
                  <FormControl>
                    <Input placeholder="例：法院邮件" disabled={isPending} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />

              <FormField control={createForm.control} name="source_type" render={({ field }) => (
                <FormItem>
                  <FormLabel>来源类型 <span className="text-destructive">*</span></FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isPending}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="请选择来源类型" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {Object.entries(SOURCE_TYPE_LABELS).map(([v, l]) => (
                        <SelectItem key={v} value={v}>{l}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />

              <FormField control={createForm.control} name="credential_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>关联凭证 <span className="text-destructive">*</span></FormLabel>
                  <Select
                    onValueChange={(v) => field.onChange(Number(v))}
                    value={field.value?.toString()}
                    disabled={isPending || isLoadingCredentials}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder={isLoadingCredentials ? '加载中...' : '请选择关联凭证'} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {credentials.map((c) => (
                        <SelectItem key={c.id} value={c.id.toString()}>
                          {c.site_name} ({c.account})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />

              <FormField control={createForm.control} name="poll_interval_minutes" render={({ field }) => (
                <FormItem>
                  <FormLabel>轮询间隔（分钟）</FormLabel>
                  <FormControl>
                    <Input type="number" min={1} max={1440} disabled={isPending} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />

              <FormField control={createForm.control} name="is_enabled" render={({ field }) => (
                <FormItem className="flex items-center gap-3">
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} disabled={isPending} />
                  </FormControl>
                  <FormLabel className="!mt-0">启用</FormLabel>
                </FormItem>
              )} />

              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
                  <X className="mr-1.5 size-4" />取消
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? <><Loader2 className="mr-1.5 size-4 animate-spin" />保存中...</> : <><Save className="mr-1.5 size-4" />添加</>}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default MessageSourceFormDialog
