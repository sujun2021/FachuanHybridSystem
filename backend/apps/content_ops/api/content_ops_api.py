from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from django.http import FileResponse, HttpRequest, HttpResponse, HttpResponseBase
from ninja import Router

from apps.content_ops.schemas.content_ops_schemas import (
    ArticleUpdateIn,
    ContentTaskCreateIn,
    ContentTaskOut,
    DiscussionScriptOut,
    DiscussionTurnOut,
    DiscussionTurnUpdateIn,
    GeneratedArticleOut,
    HotTopicOut,
    HotTopicRefreshIn,
    PodcastEpisodeOut,
    ReviewActionIn,
    TopicInspirationIn,
    TopicSuggestionOut,
    TTSTestIn,
)
from apps.content_ops.services.task_service import ContentOpsTaskService
from apps.content_ops.services.tts_service import TTS_VOICES, TTSService
from apps.core.security.auth import JWTOrSessionAuth

logger = logging.getLogger("apps.content_ops.api")

router = Router(tags=["内容运营"], auth=JWTOrSessionAuth())
_task_service = ContentOpsTaskService()


@router.post("/tts/test")
def tts_test(request: HttpRequest, payload: TTSTestIn) -> dict[str, str] | FileResponse | HttpResponse:
    if not payload.text.strip():
        return {"error": "text 不能为空"}
    if len(payload.text) > 2000:
        return {"error": "text 不能超过 2000 字"}
    if not payload.style_prompt and payload.voice not in TTS_VOICES:
        return {"error": f"不支持的音色: {payload.voice}，可选: {', '.join(TTS_VOICES.keys())}"}

    try:
        audio_bytes = TTSService().synthesize(
            text=payload.text,
            voice=payload.voice,
            audio_format=payload.audio_format,
            style_prompt=payload.style_prompt or None,
        )
    except Exception as exc:
        logger.error("TTS test failed: %s", exc)
        return {"error": str(exc)}

    suffix = f".{payload.audio_format}"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(audio_bytes)
    tmp.flush()
    tmp.close()

    content_type = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
        "pcm16": "audio/pcm",
    }.get(payload.audio_format, "audio/mpeg")

    return FileResponse(
        Path(tmp.name).open("rb"),
        content_type=content_type,
        filename=f"tts_test{suffix}",
    )


@router.get("/topics/suggest", response=list[TopicSuggestionOut])
def topic_suggest(request: HttpRequest, model: str = "") -> list[dict[str, str]]:
    from apps.content_ops.services.topic_service import TopicService

    return TopicService().suggest(model or None).topics


@router.get("/topics/hot", response=list[HotTopicOut])
def get_hot_topics(request: HttpRequest, source: str | None = None) -> list[dict[str, Any]]:
    from apps.content_ops.services.hot_topic_service import HotTopicService

    items = HotTopicService().get_hot_topics(source=source or None)
    return [
        {
            "rank": item.rank,
            "title": item.title,
            "heat": item.heat,
            "url": item.url,
            "source": item.source,
        }
        for item in items
    ]


@router.post("/topics/hot/refresh", response=list[HotTopicOut])
def refresh_hot_topics(request: HttpRequest, payload: HotTopicRefreshIn) -> list[dict[str, Any]]:
    from apps.content_ops.services.hot_topic_service import HotTopicService

    items = HotTopicService().refresh(source=payload.source or None)
    return [
        {
            "rank": item.rank,
            "title": item.title,
            "heat": item.heat,
            "url": item.url,
            "source": item.source,
        }
        for item in items
    ]


@router.post("/topics/inspiration", response=list[TopicSuggestionOut])
def topic_inspiration(request: HttpRequest, payload: TopicInspirationIn) -> list[dict[str, str]]:
    from apps.content_ops.services.hot_topic_service import HotTopicService
    from apps.content_ops.services.topic_service import TopicService

    hot_topics = HotTopicService().get_hot_topics()
    if not hot_topics:
        return []
    return TopicService().suggest_from_trends(hot_topics=hot_topics, model=payload.model or None).topics


@router.post("/tasks", response=ContentTaskOut)
def create_task(request: HttpRequest, payload: ContentTaskCreateIn) -> ContentTaskOut:
    return _task_to_out(_task_service.create_task(payload=payload, user=request.user))


@router.get("/tasks", response=list[ContentTaskOut])
def list_tasks(request: HttpRequest, mode: str | None = None) -> list[ContentTaskOut]:
    return [_task_to_out(task) for task in _task_service.list_tasks(user=request.user, mode=mode)]


@router.get("/tasks/{task_id}", response=ContentTaskOut)
def get_task(request: HttpRequest, task_id: int) -> ContentTaskOut:
    return _task_to_out(_task_service.get_task(task_id=task_id, user=request.user))


@router.post("/tasks/{task_id}/retry", response=ContentTaskOut)
def retry_task(request: HttpRequest, task_id: int) -> ContentTaskOut:
    return _task_to_out(_task_service.retry_task(task_id=task_id, user=request.user))


@router.post("/tasks/{task_id}/cancel", response=ContentTaskOut)
def cancel_task(request: HttpRequest, task_id: int) -> ContentTaskOut:
    return _task_to_out(_task_service.cancel_task(task_id=task_id, user=request.user))


@router.delete("/tasks/{task_id}")
def delete_task(request: HttpRequest, task_id: int) -> dict[str, bool]:
    _task_service.delete_task(task_id=task_id, user=request.user)
    return {"success": True}


@router.get("/tasks/{task_id}/articles", response=list[GeneratedArticleOut])
def list_articles(request: HttpRequest, task_id: int) -> list[GeneratedArticleOut]:
    return [_article_to_out(article) for article in _task_service.list_articles(task_id=task_id, user=request.user)]


@router.put("/articles/{article_id}", response=GeneratedArticleOut)
def update_article(request: HttpRequest, article_id: int, payload: ArticleUpdateIn) -> GeneratedArticleOut:
    article = _task_service.update_article(
        article_id=article_id,
        title=payload.title,
        content=payload.content,
        user=request.user,
    )
    return _article_to_out(article)


@router.post("/articles/{article_id}/regenerate", response=GeneratedArticleOut)
def regenerate_article(request: HttpRequest, article_id: int) -> GeneratedArticleOut:
    return _article_to_out(_task_service.regenerate_article(article_id=article_id, user=request.user))


@router.get("/tasks/{task_id}/episodes", response=list[PodcastEpisodeOut])
def list_episodes(request: HttpRequest, task_id: int) -> list[PodcastEpisodeOut]:
    return [_episode_to_out(episode) for episode in _task_service.list_episodes(task_id=task_id, user=request.user)]


@router.get("/tasks/{task_id}/discussions", response=list[DiscussionScriptOut])
def list_discussion_scripts(request: HttpRequest, task_id: int) -> list[DiscussionScriptOut]:
    scripts = _task_service.list_discussion_scripts(task_id=task_id, user=request.user)
    return [_discussion_script_to_out(script) for script in scripts]


@router.get("/discussions/{script_id}", response=DiscussionScriptOut)
def get_discussion_script(request: HttpRequest, script_id: int) -> DiscussionScriptOut:
    return _discussion_script_to_out(_task_service.get_discussion_script(script_id=script_id, user=request.user))


@router.put("/discussions/turns/{turn_id}", response=DiscussionTurnOut)
def update_discussion_turn(request: HttpRequest, turn_id: int, payload: DiscussionTurnUpdateIn) -> DiscussionTurnOut:
    turn = _task_service.update_discussion_turn(
        turn_id=turn_id,
        text=payload.text,
        speaker_style_prompt=payload.speaker_style_prompt,
        user=request.user,
    )
    return _discussion_turn_to_out(turn)


@router.post("/discussions/{script_id}/approve", response=DiscussionScriptOut)
def approve_discussion_script(request: HttpRequest, script_id: int, payload: ReviewActionIn) -> DiscussionScriptOut:
    script = _task_service.approve_discussion_script(script_id=script_id, user=request.user, notes=payload.notes)
    return _discussion_script_to_out(script)


@router.post("/discussions/{script_id}/reject", response=DiscussionScriptOut)
def reject_discussion_script(request: HttpRequest, script_id: int, payload: ReviewActionIn) -> DiscussionScriptOut:
    script = _task_service.reject_discussion_script(script_id=script_id, user=request.user, notes=payload.notes)
    return _discussion_script_to_out(script)


@router.post("/discussions/{script_id}/regenerate", response=DiscussionScriptOut)
def regenerate_discussion_script(request: HttpRequest, script_id: int) -> DiscussionScriptOut:
    return _discussion_script_to_out(_task_service.regenerate_discussion_script(script_id=script_id, user=request.user))


@router.post("/discussions/{script_id}/synthesize", response=PodcastEpisodeOut)
def synthesize_discussion(request: HttpRequest, script_id: int) -> PodcastEpisodeOut:
    return _episode_to_out(_task_service.synthesize_discussion(script_id=script_id, user=request.user))


@router.post("/articles/{article_id}/approve", response=GeneratedArticleOut)
def approve_article(request: HttpRequest, article_id: int, payload: ReviewActionIn) -> GeneratedArticleOut:
    return _article_to_out(_task_service.approve_article(article_id=article_id, user=request.user, notes=payload.notes))


@router.post("/articles/{article_id}/reject", response=GeneratedArticleOut)
def reject_article(request: HttpRequest, article_id: int, payload: ReviewActionIn) -> GeneratedArticleOut:
    return _article_to_out(_task_service.reject_article(article_id=article_id, user=request.user, notes=payload.notes))


@router.post("/episodes/{episode_id}/approve", response=PodcastEpisodeOut)
def approve_episode(request: HttpRequest, episode_id: int, payload: ReviewActionIn) -> PodcastEpisodeOut:
    return _episode_to_out(_task_service.approve_episode(episode_id=episode_id, user=request.user, notes=payload.notes))


@router.post("/episodes/{episode_id}/reject", response=PodcastEpisodeOut)
def reject_episode(request: HttpRequest, episode_id: int, payload: ReviewActionIn) -> PodcastEpisodeOut:
    return _episode_to_out(_task_service.reject_episode(episode_id=episode_id, user=request.user, notes=payload.notes))


@router.get("/episodes/{episode_id}/audio")
def episode_audio(request: HttpRequest, episode_id: int) -> dict[str, str] | FileResponse | HttpResponseBase:
    from apps.content_ops.models import PodcastEpisode
    from apps.core.http.streaming import build_range_file_response

    episode = PodcastEpisode.objects.filter(id=episode_id).first()
    if not episode or not episode.audio_file:
        return {"error": "音频不存在"}
    return build_range_file_response(request, episode.audio_file.path)


@router.get("/rss", auth=None)
def podcast_rss_feed(request: HttpRequest) -> HttpResponse:
    from apps.content_ops.services.rss_service import RSSService

    host = request.get_host()
    scheme = "https" if request.is_secure() else "http"
    xml = RSSService().generate_feed(request_host=f"{scheme}://{host}")
    return HttpResponse(xml, content_type="application/rss+xml; charset=utf-8")


def _task_to_out(task: Any) -> ContentTaskOut:
    return ContentTaskOut(
        id=task.pk,
        mode=task.mode,
        keyword=task.keyword,
        case_summary=task.case_summary,
        voice=task.voice,
        tts_style_prompt=task.tts_style_prompt,
        output_mode=task.output_mode or "narration",
        discussion_speakers=task.discussion_speakers or [],
        source_title=task.source_title,
        source_court_text=task.source_court_text,
        source_judgment_date=task.source_judgment_date,
        status=task.status,
        progress=task.progress,
        message=task.message,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _article_to_out(article: Any) -> GeneratedArticleOut:
    return GeneratedArticleOut(
        id=article.pk,
        title=article.title,
        content=article.content,
        source_summary=article.source_summary,
        review_status=article.review_status,
        reviewer_notes=article.reviewer_notes,
        llm_model=article.llm_model,
        token_usage=article.token_usage or {},
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _episode_to_out(episode: Any) -> PodcastEpisodeOut:
    return PodcastEpisodeOut(
        id=episode.pk,
        article_id=episode.article_id,
        discussion_script_id=episode.discussion_script_id,
        content_source=episode.content_source or "article",
        voice=episode.voice,
        audio_url=episode.audio_file.url if episode.audio_file else "",
        duration_seconds=episode.duration_seconds,
        file_size_bytes=episode.file_size_bytes,
        review_status=episode.review_status,
        reviewer_notes=episode.reviewer_notes,
        created_at=episode.created_at,
        updated_at=episode.updated_at,
    )


def _discussion_turn_to_out(turn: Any) -> DiscussionTurnOut:
    return DiscussionTurnOut(
        id=turn.pk,
        speaker_name=turn.speaker_name,
        speaker_style_prompt=turn.speaker_style_prompt,
        text=turn.text,
        order=turn.order,
    )


def _discussion_script_to_out(script: Any) -> DiscussionScriptOut:
    turns = list(script.turns.order_by("order"))
    return DiscussionScriptOut(
        id=script.pk,
        title=script.title,
        topic=script.topic,
        review_status=script.review_status,
        reviewer_notes=script.reviewer_notes,
        turns=[_discussion_turn_to_out(turn) for turn in turns],
        llm_model=script.llm_model,
        token_usage=script.token_usage or {},
        created_at=script.created_at,
        updated_at=script.updated_at,
    )
