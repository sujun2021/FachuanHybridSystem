import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { ArrowLeft, FileWarning } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { TemplateForm } from '@/features/templates'
import { useTemplate } from '@/features/templates/hooks/use-template'
import { useTemplateMutations } from '@/features/templates/hooks/use-template-mutations'
import { PATHS } from '@/routes/paths'

export default function TemplateEditPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const templateId = Number(id)
  const { data: template, isLoading, error } = useTemplate(templateId)
  const { update } = useTemplateMutations()

  const handleBack = () => navigate(PATHS.ADMIN_TEMPLATES)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="bg-muted h-8 w-48 animate-pulse rounded" />
        <div className="bg-muted h-64 w-full animate-pulse rounded-lg" />
      </div>
    )
  }

  if (error || !template) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <FileWarning className="text-muted-foreground mb-4 size-16 opacity-50" />
        <h2 className="mb-2 text-xl font-semibold">模板不存在</h2>
        <p className="text-muted-foreground mb-6">您访问的模板可能已被删除或不存在</p>
        <Button onClick={handleBack} variant="outline">
          <ArrowLeft className="mr-2 size-4" />返回列表
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">编辑文件模板</h1>
        <p className="text-muted-foreground text-sm mt-1">
          修改模板「{template.name}」的配置信息
        </p>
      </div>
      <TemplateForm
        template={template}
        onSubmit={(data) => {
          update.mutate(
            { id: templateId, data },
            {
              onSuccess: () => {
                toast.success('模板更新成功')
                navigate(PATHS.ADMIN_TEMPLATES)
              },
              onError: (err) => {
                toast.error(err.message || '更新失败，请重试')
              },
            },
          )
        }}
      />
    </div>
  )
}
