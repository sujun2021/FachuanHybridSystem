import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentOpsApi } from '../api'
import type { CreateTaskInput, ReviewActionInput, TopicSuggestion } from '../types'

// 选题建议（手动触发，使用 mutation）
export function useTopicSuggestions() {
  const [data, setData] = useState<TopicSuggestion[] | null>(null)
  const mutation = useMutation({
    mutationFn: () => contentOpsApi.suggestTopics(),
    onSuccess: (result) => setData(result),
  })

  return {
    data,
    isFetching: mutation.isPending,
    refetch: () => mutation.mutateAsync(),
  }
}

// 任务列表
export function useTaskList(mode?: string) {
  return useQuery({
    queryKey: ['content-ops', 'tasks', mode],
    queryFn: () => contentOpsApi.listTasks(mode),
    refetchInterval: (query) => {
      // 有运行中的任务时自动刷新
      const tasks = query.state.data
      if (tasks?.some((t) => ['pending', 'queued', 'running'].includes(t.status))) {
        return 3000
      }
      return false
    },
  })
}

// 任务详情
export function useTaskDetail(taskId: number | null) {
  return useQuery({
    queryKey: ['content-ops', 'task', taskId],
    queryFn: () => contentOpsApi.getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const task = query.state.data
      if (task && ['pending', 'queued', 'running'].includes(task.status)) {
        return 2000
      }
      return false
    },
  })
}

// 任务关联文章
export function useTaskArticles(taskId: number | null) {
  return useQuery({
    queryKey: ['content-ops', 'task', taskId, 'articles'],
    queryFn: () => contentOpsApi.getTaskArticles(taskId!),
    enabled: !!taskId,
  })
}

// 任务关联音频
export function useTaskEpisodes(taskId: number | null) {
  return useQuery({
    queryKey: ['content-ops', 'task', taskId, 'episodes'],
    queryFn: () => contentOpsApi.getTaskEpisodes(taskId!),
    enabled: !!taskId,
  })
}

// 创建任务
export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTaskInput) => contentOpsApi.createTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-ops', 'tasks'] })
    },
  })
}

// 审核文章
export function useReviewArticle() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ articleId, action, notes }: { articleId: number; action: 'approve' | 'reject'; notes?: string }) => {
      const data: ReviewActionInput = { notes }
      return action === 'approve'
        ? contentOpsApi.approveArticle(articleId, data)
        : contentOpsApi.rejectArticle(articleId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-ops'] })
    },
  })
}

// 审核音频
export function useReviewEpisode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ episodeId, action, notes }: { episodeId: number; action: 'approve' | 'reject'; notes?: string }) => {
      const data: ReviewActionInput = { notes }
      return action === 'approve'
        ? contentOpsApi.approveEpisode(episodeId, data)
        : contentOpsApi.rejectEpisode(episodeId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-ops'] })
    },
  })
}
