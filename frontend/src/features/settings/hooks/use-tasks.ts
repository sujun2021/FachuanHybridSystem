/**
 * useTasks Hooks
 * 任务队列数据查询
 */

import { useQuery } from '@tanstack/react-query'
import { taskQueueApi } from '../api'

export function useQueuedTasks() {
  return useQuery({
    queryKey: ['task-queue', 'queued'],
    queryFn: () => taskQueueApi.listQueued(),
    staleTime: 10 * 1000,
  })
}

export function useCompletedTasks() {
  return useQuery({
    queryKey: ['task-queue', 'completed'],
    queryFn: () => taskQueueApi.listCompleted(),
    staleTime: 30 * 1000,
  })
}

export function useFailedTasks() {
  return useQuery({
    queryKey: ['task-queue', 'failed'],
    queryFn: () => taskQueueApi.listFailed(),
    staleTime: 30 * 1000,
  })
}

export function useScheduledTasks() {
  return useQuery({
    queryKey: ['task-queue', 'scheduled'],
    queryFn: () => taskQueueApi.listScheduled(),
    staleTime: 30 * 1000,
  })
}
