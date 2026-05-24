import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Plus, Sparkles, FileInput } from 'lucide-react'
import { TopicInspiration } from './TopicInspiration'
import { DirectInput } from './DirectInput'
import { TaskList } from './TaskList'
import { TaskDetail } from './TaskDetail'
import { CreateTaskDialog } from './CreateTaskDialog'
import type { TopicSuggestion } from '../types'

export function ContentWorkbench() {
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogKeyword, setDialogKeyword] = useState('')
  const [dialogCaseSummary, setDialogCaseSummary] = useState('')

  const handleSelectTopic = (topic: TopicSuggestion) => {
    setDialogKeyword(topic.suggested_keyword)
    setDialogCaseSummary(`${topic.title}：${topic.description}`)
    setDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">内容运营</h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI 驱动的法律内容创作工作台 — 从选题到生成文章和播客音频
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="w-4 h-4 mr-1.5" />
          新建任务
        </Button>
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        {/* 左侧：创作区 */}
        <div className="space-y-6 min-w-0">
          <Tabs defaultValue="topics">
            <TabsList>
              <TabsTrigger value="topics">
                <Sparkles className="w-4 h-4 mr-1" />
                选题灵感
              </TabsTrigger>
              <TabsTrigger value="direct">
                <FileInput className="w-4 h-4 mr-1" />
                直投内容
              </TabsTrigger>
            </TabsList>

            <TabsContent value="topics" className="mt-4">
              <TopicInspiration onSelectTopic={handleSelectTopic} />
            </TabsContent>

            <TabsContent value="direct" className="mt-4">
              <DirectInput onTaskCreated={setSelectedTaskId} />
            </TabsContent>
          </Tabs>

          {/* 任务详情区 */}
          {selectedTaskId && (
            <div className="border-t pt-6">
              <TaskDetail taskId={selectedTaskId} />
            </div>
          )}
        </div>

        {/* 右侧：任务列表 */}
        <div className="lg:border-l lg:pl-6">
          <TaskList
            selectedTaskId={selectedTaskId}
            onSelectTask={setSelectedTaskId}
          />
        </div>
      </div>

      {/* 创建任务对话框 */}
      <CreateTaskDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        defaultKeyword={dialogKeyword}
        defaultCaseSummary={dialogCaseSummary}
        defaultMode={dialogKeyword ? 'search' : 'direct'}
      />
    </div>
  )
}
