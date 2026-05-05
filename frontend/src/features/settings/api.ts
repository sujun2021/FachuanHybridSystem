/**
 * Task Queue API
 */

import { createApiClient } from '@/lib/api'

export interface QueuedTask {
  id: string
  name: string
  func: string
  group: string | null
  created_at: string | null
}

export interface CompletedTask {
  id: string
  name: string
  func: string
  group: string | null
  started_at: string | null
  finished_at: string | null
  duration: number | null
  success: boolean
  result: string | null
}

export interface ScheduledTask {
  id: number
  name: string
  func: string
  schedule_type: string
  repeats: number
  next_run: string | null
  last_run: string | null
}

const api = createApiClient({
  prefixUrl: `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1'}/task-queue`,
})

export const taskQueueApi = {
  listQueued: (): Promise<QueuedTask[]> =>
    api.get('queued').json<QueuedTask[]>(),

  listCompleted: (): Promise<CompletedTask[]> =>
    api.get('completed').json<CompletedTask[]>(),

  listFailed: (): Promise<CompletedTask[]> =>
    api.get('failed').json<CompletedTask[]>(),

  listScheduled: (): Promise<ScheduledTask[]> =>
    api.get('scheduled').json<ScheduledTask[]>(),

  deleteTask: (taskId: string): Promise<{ deleted: number }> =>
    api.delete(`tasks/${taskId}`).json(),

  deleteSchedule: (scheduleId: number): Promise<{ deleted: number }> =>
    api.delete(`schedules/${scheduleId}`).json(),

  resubmitTask: (taskId: string): Promise<{ new_task_id?: string; error?: string }> =>
    api.post(`tasks/${taskId}/resubmit`).json(),
}

export default taskQueueApi
