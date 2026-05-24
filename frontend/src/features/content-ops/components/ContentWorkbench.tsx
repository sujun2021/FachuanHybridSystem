import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, Sparkles, FileInput, LayoutList } from 'lucide-react'
import { TopicInspiration } from './TopicInspiration'
import { DirectInput } from './DirectInput'
import { TaskList } from './TaskList'
import { TaskDetail } from './TaskDetail'
import { CreateTaskDialog } from './CreateTaskDialog'
import type { TopicSuggestion } from '../types'

export function ContentWorkbench() {
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [dialogKeyword, setDialogKeyword] = useState('')
  const [dialogCaseSummary, setDialogCaseSummary] = useState('')

  const handleSelectTopic = (topic: TopicSuggestion) => {
    setDialogKeyword(topic.suggested_keyword)
    setDialogCaseSummary(`${topic.title}：${topic.description}`)
    setDialogOpen(true)
  }

  const handleSelectTask = (taskId: number) => {
    setSelectedTaskId(taskId)
    setDetailOpen(true)
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
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
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
              <DirectInput onTaskCreated={handleSelectTask} />
            </TabsContent>
          </Tabs>
        </div>

        {/* 右侧：任务列表 */}
        <div className="lg:border-l lg:pl-6">
          <Card className="border-0 shadow-none bg-muted/30">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <LayoutList className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">任务记录</h3>
              </div>
              <TaskList
                selectedTaskId={selectedTaskId}
                onSelectTask={handleSelectTask}
              />
            </CardContent>
          </Card>
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

      {/* 任务详情对话框 */}
      {selectedTaskId && detailOpen && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
          <div className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl border-l bg-background shadow-lg">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b px-6 py-4">
                <h2 className="text-lg font-semibold">任务详情</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDetailOpen(false)}
                >
                  关闭
                </Button>
              </div>
              <div className="flex-1 overflow-y-auto p-6">
                <TaskDetail taskId={selectedTaskId} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
