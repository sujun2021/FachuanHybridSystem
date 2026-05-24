import { createFeatureApiClient, resolveMediaUrl } from '@/lib/api'
import type {
  ContentTask,
  CreateTaskInput,
  GeneratedArticle,
  PodcastEpisode,
  ReviewActionInput,
  TopicSuggestion,
} from './types'

const api = createFeatureApiClient('content-ops')

export const contentOpsApi = {
  // 选题建议（LLM 调用耗时较长，需要更长超时）
  suggestTopics: () =>
    api.get('topics/suggest', { timeout: 120_000 }).json<TopicSuggestion[]>(),

  // 任务 CRUD
  createTask: (data: CreateTaskInput) =>
    api.post('tasks', { json: data }).json<ContentTask>(),

  listTasks: (mode?: string) =>
    api.get('tasks', { searchParams: mode ? { mode } : undefined }).json<ContentTask[]>(),

  getTask: (taskId: number) =>
    api.get(`tasks/${taskId}`).json<ContentTask>(),

  // 任务关联数据
  getTaskArticles: (taskId: number) =>
    api.get(`tasks/${taskId}/articles`).json<GeneratedArticle[]>(),

  getTaskEpisodes: (taskId: number) =>
    api.get(`tasks/${taskId}/episodes`).json<PodcastEpisode[]>(),

  // 审核操作
  approveArticle: (articleId: number, data?: ReviewActionInput) =>
    api.post(`articles/${articleId}/approve`, { json: data ?? {} }).json<GeneratedArticle>(),

  rejectArticle: (articleId: number, data?: ReviewActionInput) =>
    api.post(`articles/${articleId}/reject`, { json: data ?? {} }).json<GeneratedArticle>(),

  approveEpisode: (episodeId: number, data?: ReviewActionInput) =>
    api.post(`episodes/${episodeId}/approve`, { json: data ?? {} }).json<PodcastEpisode>(),

  rejectEpisode: (episodeId: number, data?: ReviewActionInput) =>
    api.post(`episodes/${episodeId}/reject`, { json: data ?? {} }).json<PodcastEpisode>(),

  // 音频 URL
  getAudioUrl: (episodeId: number) =>
    resolveMediaUrl(`/api/v1/content-ops/episodes/${episodeId}/audio`),

  // TTS 测试
  testTts: (text: string, voice: string, stylePrompt?: string) =>
    api.post('tts/test', {
      json: { text, voice, audio_format: 'mp3', style_prompt: stylePrompt ?? '' },
    }).blob(),
}
