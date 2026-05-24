import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  Loader2,
  FileText,
  Volume2,
  Play,
  Pause,
  Download,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTaskDetail, useTaskArticles, useTaskEpisodes, useReviewArticle, useReviewEpisode } from '../hooks/use-content-ops'
import { STATUS_LABEL, REVIEW_STATUS_LABEL } from '../types'
import type { GeneratedArticle, PodcastEpisode, ReviewStatus } from '../types'
import { contentOpsApi } from '../api'
import { toast } from 'sonner'

interface TaskDetailProps {
  taskId: number
}

export function TaskDetail({ taskId }: TaskDetailProps) {
  const { data: task, isLoading } = useTaskDetail(taskId)
  const { data: articles = [] } = useTaskArticles(taskId)
  const { data: episodes = [] } = useTaskEpisodes(taskId)

  if (isLoading || !task) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const isActive = ['pending', 'queued', 'running'].includes(task.status)

  return (
    <div className="space-y-4">
      {/* 任务头部信息 */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold">
            {task.source_title || task.keyword || `任务 #${task.id}`}
          </h3>
          <Badge variant={task.status === 'completed' ? 'default' : task.status === 'failed' ? 'destructive' : 'secondary'}>
            {STATUS_LABEL[task.status]}
          </Badge>
        </div>
        {task.source_court_text && (
          <p className="text-xs text-muted-foreground">
            {task.source_court_text}
            {task.source_judgment_date && ` · ${task.source_judgment_date}`}
          </p>
        )}
      </div>

      {/* 进度条 */}
      {isActive && (
        <Card>
          <CardContent className="pt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{task.message || '处理中...'}</span>
              <span className="font-medium">{task.progress}%</span>
            </div>
            <Progress value={task.progress} />
          </CardContent>
        </Card>
      )}

      {/* 错误信息 */}
      {task.status === 'failed' && task.error && (
        <Card className="border-destructive/50">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">{task.error}</p>
          </CardContent>
        </Card>
      )}

      {/* 文章和音频 Tab */}
      {(articles.length > 0 || episodes.length > 0) && (
        <Tabs defaultValue="articles">
          <TabsList>
            <TabsTrigger value="articles">
              <FileText className="w-4 h-4 mr-1" />
              文章 ({articles.length})
            </TabsTrigger>
            <TabsTrigger value="episodes">
              <Volume2 className="w-4 h-4 mr-1" />
              音频 ({episodes.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="articles" className="space-y-3 mt-3">
            {articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </TabsContent>

          <TabsContent value="episodes" className="space-y-3 mt-3">
            {episodes.map((episode) => (
              <EpisodeCard key={episode.id} episode={episode} />
            ))}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function ArticleCard({ article }: { article: GeneratedArticle }) {
  const [expanded, setExpanded] = useState(false)
  const [notes, setNotes] = useState('')
  const reviewArticle = useReviewArticle()

  const handleReview = (action: 'approve' | 'reject') => {
    reviewArticle.mutate(
      { articleId: article.id, action, notes: notes || undefined },
      {
        onSuccess: () => {
          toast.success(action === 'approve' ? '文章已通过' : '文章已驳回')
          setNotes('')
        },
        onError: () => toast.error('操作失败'),
      },
    )
  }

  const reviewBadge = (status: ReviewStatus) => {
    const variants = { draft: 'secondary' as const, approved: 'default' as const, rejected: 'destructive' as const }
    return <Badge variant={variants[status]}>{REVIEW_STATUS_LABEL[status]}</Badge>
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm">{article.title}</CardTitle>
            <CardDescription className="text-xs mt-0.5">
              {article.llm_model && <span>模型: {article.llm_model}</span>}
              {article.token_usage && (
                <span className="ml-2">Token: {article.token_usage.total_tokens}</span>
              )}
            </CardDescription>
          </div>
          {reviewBadge(article.review_status)}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {article.source_summary && (
          <p className="text-xs text-muted-foreground italic">{article.source_summary}</p>
        )}

        <div className={cn('text-sm whitespace-pre-wrap', !expanded && 'line-clamp-6')}>
          {article.content}
        </div>
        {article.content.length > 300 && (
          <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)}>
            {expanded ? '收起' : '展开全文'}
          </Button>
        )}

        {/* 审核操作 */}
        {article.review_status === 'draft' && (
          <div className="space-y-2 pt-2 border-t">
            <Textarea
              placeholder="审核备注（可选）"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="text-xs"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="default"
                onClick={() => handleReview('approve')}
                disabled={reviewArticle.isPending}
              >
                <ThumbsUp className="w-3.5 h-3.5 mr-1" />
                通过
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => handleReview('reject')}
                disabled={reviewArticle.isPending}
              >
                <ThumbsDown className="w-3.5 h-3.5 mr-1" />
                驳回
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function EpisodeCard({ episode }: { episode: PodcastEpisode }) {
  const [playing, setPlaying] = useState(false)
  const [notes, setNotes] = useState('')
  const reviewEpisode = useReviewEpisode()
  const audioUrl = contentOpsApi.getAudioUrl(episode.id)

  const handleReview = (action: 'approve' | 'reject') => {
    reviewEpisode.mutate(
      { episodeId: episode.id, action, notes: notes || undefined },
      {
        onSuccess: () => {
          toast.success(action === 'approve' ? '音频已通过' : '音频已驳回')
          setNotes('')
        },
        onError: () => toast.error('操作失败'),
      },
    )
  }

  const handlePlay = () => {
    const audio = document.getElementById(`audio-${episode.id}`) as HTMLAudioElement
    if (audio) {
      if (playing) {
        audio.pause()
      } else {
        audio.play()
      }
      setPlaying(!playing)
    }
  }

  const reviewBadge = (status: ReviewStatus) => {
    const variants = { draft: 'secondary' as const, approved: 'default' as const, rejected: 'destructive' as const }
    return <Badge variant={variants[status]}>{REVIEW_STATUS_LABEL[status]}</Badge>
  }

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button size="icon" variant="outline" className="h-8 w-8" onClick={handlePlay}>
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </Button>
            <div>
              <p className="text-sm font-medium">音色: {episode.voice}</p>
              <p className="text-[10px] text-muted-foreground">
                {episode.duration_seconds && `${Math.round(episode.duration_seconds)}秒`}
                {episode.file_size_bytes && ` · ${(episode.file_size_bytes / 1024 / 1024).toFixed(1)}MB`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {reviewBadge(episode.review_status)}
            <a href={audioUrl ?? undefined} download>
              <Button size="icon" variant="ghost" className="h-8 w-8">
                <Download className="w-4 h-4" />
              </Button>
            </a>
          </div>
        </div>

        <audio
          id={`audio-${episode.id}`}
          src={audioUrl ?? undefined}
          onEnded={() => setPlaying(false)}
          className="hidden"
        />

        {/* 审核操作 */}
        {episode.review_status === 'draft' && (
          <div className="space-y-2 pt-2 border-t">
            <Textarea
              placeholder="审核备注（可选）"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="text-xs"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="default"
                onClick={() => handleReview('approve')}
                disabled={reviewEpisode.isPending}
              >
                <ThumbsUp className="w-3.5 h-3.5 mr-1" />
                通过
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => handleReview('reject')}
                disabled={reviewEpisode.isPending}
              >
                <ThumbsDown className="w-3.5 h-3.5 mr-1" />
                驳回
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
