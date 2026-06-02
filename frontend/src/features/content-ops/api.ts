import { createFeatureApiClient, resolveMediaUrl } from '@/lib/api'
import { getAccessToken } from '@/lib/token'
import type {
  ContentTask,
  CreateTaskInput,
  DiscussionScript,
  DiscussionTurn,
  GeneratedArticle,
  HotTopic,
  PodcastEpisode,
  ReviewActionInput,
  TopicSuggestion,
} from './types'

const api = createFeatureApiClient('content-ops')

export const contentOpsApi = {
  suggestTopics: (model?: string) =>
    api.get('topics/suggest', {
      timeout: 120_000,
      searchParams: model ? { model } : undefined,
    }).json<TopicSuggestion[]>(),

  getHotTopics: (source?: string) =>
    api.get('topics/hot', { searchParams: source ? { source } : undefined }).json<HotTopic[]>(),

  refreshHotTopics: (source?: string) =>
    api.post('topics/hot/refresh', { json: { source: source || '' } }).json<HotTopic[]>(),

  getInspiration: (model?: string) =>
    api.post('topics/inspiration', {
      json: { model: model || '' },
      timeout: 120_000,
    }).json<TopicSuggestion[]>(),

  createTask: (data: CreateTaskInput) =>
    api.post('tasks', { json: data }).json<ContentTask>(),

  listTasks: (mode?: string) =>
    api.get('tasks', { searchParams: mode ? { mode } : undefined }).json<ContentTask[]>(),

  getTask: (taskId: number) =>
    api.get(`tasks/${taskId}`).json<ContentTask>(),

  retryTask: (taskId: number) =>
    api.post(`tasks/${taskId}/retry`).json<ContentTask>(),

  cancelTask: (taskId: number) =>
    api.post(`tasks/${taskId}/cancel`).json<ContentTask>(),

  deleteTask: (taskId: number) =>
    api.delete(`tasks/${taskId}`).json<{ success: boolean }>(),

  getTaskArticles: (taskId: number) =>
    api.get(`tasks/${taskId}/articles`).json<GeneratedArticle[]>(),

  updateArticle: (articleId: number, data: { title?: string; content?: string }) =>
    api.put(`articles/${articleId}`, { json: data }).json<GeneratedArticle>(),

  regenerateArticle: (articleId: number) =>
    api.post(`articles/${articleId}/regenerate`).json<GeneratedArticle>(),

  getTaskEpisodes: (taskId: number) =>
    api.get(`tasks/${taskId}/episodes`).json<PodcastEpisode[]>(),

  getTaskDiscussions: (taskId: number) =>
    api.get(`tasks/${taskId}/discussions`).json<DiscussionScript[]>(),

  getDiscussion: (scriptId: number) =>
    api.get(`discussions/${scriptId}`).json<DiscussionScript>(),

  updateDiscussionTurn: (turnId: number, data: { text?: string; speaker_style_prompt?: string }) =>
    api.put(`discussions/turns/${turnId}`, { json: data }).json<DiscussionTurn>(),

  approveDiscussion: (scriptId: number, data?: ReviewActionInput) =>
    api.post(`discussions/${scriptId}/approve`, { json: data ?? {} }).json<DiscussionScript>(),

  rejectDiscussion: (scriptId: number, data?: ReviewActionInput) =>
    api.post(`discussions/${scriptId}/reject`, { json: data ?? {} }).json<DiscussionScript>(),

  regenerateDiscussion: (scriptId: number) =>
    api.post(`discussions/${scriptId}/regenerate`).json<DiscussionScript>(),

  synthesizeDiscussion: (scriptId: number) =>
    api.post(`discussions/${scriptId}/synthesize`, { timeout: 600_000 }).json<PodcastEpisode>(),

  approveArticle: (articleId: number, data?: ReviewActionInput) =>
    api.post(`articles/${articleId}/approve`, { json: data ?? {} }).json<GeneratedArticle>(),

  rejectArticle: (articleId: number, data?: ReviewActionInput) =>
    api.post(`articles/${articleId}/reject`, { json: data ?? {} }).json<GeneratedArticle>(),

  approveEpisode: (episodeId: number, data?: ReviewActionInput) =>
    api.post(`episodes/${episodeId}/approve`, { json: data ?? {} }).json<PodcastEpisode>(),

  rejectEpisode: (episodeId: number, data?: ReviewActionInput) =>
    api.post(`episodes/${episodeId}/reject`, { json: data ?? {} }).json<PodcastEpisode>(),

  getAudioUrl: (episodeId: number) => {
    const base = resolveMediaUrl(`/api/v1/content-ops/episodes/${episodeId}/audio`)
    if (!base) return null
    const token = getAccessToken()
    return token ? `${base}?token=${token}` : base
  },

  testTts: (text: string, voice: string, stylePrompt?: string) =>
    api.post('tts/test', {
      json: { text, voice, audio_format: 'mp3', style_prompt: stylePrompt ?? '' },
    }).blob(),
}
