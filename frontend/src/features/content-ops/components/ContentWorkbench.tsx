import { useState } from 'react'
import { useNavigate } from 'react-router'
import { motion, AnimatePresence } from 'framer-motion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Plus, Sparkles, FileInput, ArrowRight } from 'lucide-react'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { TopicInspiration } from './TopicInspiration'
import { DirectInput } from './DirectInput'
import { TaskList } from './TaskList'
import { TaskDetail } from './TaskDetail'
import { CreateTaskDialog } from './CreateTaskDialog'
import { PATHS } from '@/routes/paths'
import type { TopicSuggestion } from '../types'

export function ContentWorkbench() {
  const navigate = useNavigate()
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
    <ErrorBoundary>
      <motion.div
        className="flex flex-col h-[calc(100vh-8rem)]"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        {/* 椤甸潰鏍囬鏍?*/}
        <div className="flex items-center justify-between pb-4 border-b">
          <div>
            <h1 className="text-xl font-bold tracking-tight">鍐呭杩愯惀</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              AI 椹卞姩鐨勬硶寰嬪唴瀹瑰垱浣?鈥?浠庨€夐鍒扮敓鎴愭枃绔犲拰鎾闊抽
            </p>
          </div>
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            <Plus className="w-3.5 h-3.5 mr-1" />
            鏂板缓浠诲姟
          </Button>
        </div>

        {/* 涓诲唴瀹瑰尯 */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-0 lg:divide-x min-h-0 mt-4">
          {/* 宸︿晶锛氫换鍔″垪琛紙涓诲尯鍩燂級 */}
          <div className="min-w-0 overflow-hidden flex flex-col">
            <TaskList
              selectedTaskId={selectedTaskId}
              onSelectTask={handleSelectTask}
            />
          </div>

          {/* 鍙充晶锛氬垱浣滃伐鍏凤紙杈呭姪鍖哄煙锛?*/}
          <div className="min-w-0 overflow-hidden flex flex-col pl-0 lg:pl-5">
            <Tabs defaultValue="topics" className="flex flex-col flex-1 min-h-0">
              <TabsList className="self-start">
                <TabsTrigger value="topics" className="text-xs">
                  <Sparkles className="w-3.5 h-3.5 mr-1" />
                  閫夐鐏垫劅
                </TabsTrigger>
                <TabsTrigger value="direct" className="text-xs">
                  <FileInput className="w-3.5 h-3.5 mr-1" />
                  鐩存姇鍐呭
                </TabsTrigger>
              </TabsList>

              <div className="flex-1 min-h-0 overflow-y-auto mt-3">
                <AnimatePresence mode="wait">
                  <TabsContent value="topics" className="mt-0" asChild>
                    <motion.div
                      key="topics"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="space-y-3">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full h-8 text-xs justify-between"
                          onClick={() => navigate(PATHS.ADMIN_TOOLS_CONTENT_OPS_INSPIRATION)}
                        >
                          <span className="flex items-center gap-1">
                            <Sparkles className="w-3.5 h-3.5" />
                            鏌ョ湅瀹屾暣鐏垫劅椤碉紙鐑悳 + AI 绛涢€夛級
                          </span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Button>
                        <TopicInspiration onSelectTopic={handleSelectTopic} />
                      </div>
                    </motion.div>
                  </TabsContent>
                </AnimatePresence>

                <AnimatePresence mode="wait">
                  <TabsContent value="direct" className="mt-0" asChild>
                    <motion.div
                      key="direct"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.2 }}
                    >
                      <DirectInput onTaskCreated={handleSelectTask} />
                    </motion.div>
                  </TabsContent>
                </AnimatePresence>
              </div>
            </Tabs>
          </div>
        </div>

        {/* 鍒涘缓浠诲姟瀵硅瘽妗?*/}
        <CreateTaskDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          defaultKeyword={dialogKeyword}
          defaultCaseSummary={dialogCaseSummary}
          defaultMode={dialogKeyword ? 'search' : 'direct'}
        />

        {/* 浠诲姟璇︽儏渚ч潰鏉?*/}
        <Sheet open={detailOpen} onOpenChange={setDetailOpen}>
          <SheetContent
            side="right"
            className="w-full sm:max-w-xl p-0"
            showCloseButton={false}
          >
            <SheetHeader className="border-b px-5 py-3 flex-row items-center justify-between space-y-0">
              <SheetTitle className="text-base font-semibold">浠诲姟璇︽儏</SheetTitle>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setDetailOpen(false)}
              >
                鍏抽棴
              </Button>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto p-5">
              {selectedTaskId && <TaskDetail taskId={selectedTaskId} />}
            </div>
          </SheetContent>
        </Sheet>
      </motion.div>
    </ErrorBoundary>
  )
}
