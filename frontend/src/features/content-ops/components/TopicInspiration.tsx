import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Sparkles, RefreshCw, Search, Lightbulb } from 'lucide-react'
import { useTopicSuggestions } from '../hooks/use-content-ops'
import type { TopicSuggestion } from '../types'

interface TopicInspirationProps {
  onSelectTopic: (topic: TopicSuggestion) => void
}

export function TopicInspiration({ onSelectTopic }: TopicInspirationProps) {
  const { data: topics, isFetching, refetch } = useTopicSuggestions()
  const [hasRequested, setHasRequested] = useState(false)

  const handleSuggest = () => {
    setHasRequested(true)
    refetch()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">AI 选题推荐</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            AI 基于法律热点自动生成选题建议，点击选题直接创建检索任务
          </p>
        </div>
        <Button
          onClick={handleSuggest}
          disabled={isFetching}
          size="sm"
        >
          {isFetching ? (
            <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 mr-1.5" />
          )}
          {hasRequested ? '换一批' : 'AI 推荐选题'}
        </Button>
      </div>

      {!hasRequested && !topics && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
            <Lightbulb className="w-6 h-6 text-muted-foreground" />
          </div>
          <p className="text-sm text-muted-foreground">
            点击上方按钮，AI 将为你推荐法律故事选题
          </p>
        </div>
      )}

      {isFetching && (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-full mt-2" />
                <div className="h-3 bg-muted rounded w-2/3 mt-1" />
              </CardHeader>
              <CardContent>
                <div className="h-5 bg-muted rounded w-1/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {topics && topics.length > 0 && !isFetching && (
        <div className="grid gap-3 sm:grid-cols-2">
          {topics.map((topic: TopicSuggestion, index: number) => (
            <Card
              key={index}
              className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-sm group"
              onClick={() => onSelectTopic(topic)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm group-hover:text-primary transition-colors">
                  {topic.title}
                </CardTitle>
                <CardDescription className="text-xs line-clamp-2">
                  {topic.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    <Search className="w-3 h-3 mr-1" />
                    {topic.suggested_keyword}
                  </Badge>
                  <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                    点击创建任务 →
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {topics && topics.length === 0 && !isFetching && (
        <div className="text-center py-8 text-sm text-muted-foreground">
          暂无选题建议，请稍后重试
        </div>
      )}
    </div>
  )
}
