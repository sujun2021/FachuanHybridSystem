"""任务服务 - ContentTask 的 CRUD、审核、队列提交。"""

from __future__ import annotations

import logging
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.content_ops.models import (
    ContentTask,
    ContentTaskMode,
    ContentTaskStatus,
    DiscussionScript,
    DiscussionTurn,
    GeneratedArticle,
    PodcastEpisode,
    ReviewStatus,
)
from apps.core.exceptions.common import NotFoundError, PermissionDenied, ValidationException
from apps.core.tasking.convenience import submit_task

logger = logging.getLogger(__name__)

_QUEUED_MESSAGE = "任务已提交队列，等待执行"
_CREATE_PENDING_MESSAGE = "任务已创建，等待提交"


class ContentOpsTaskService:
    """ContentTask 的业务操作。"""

    def create_task(self, *, payload: Any, user: Any | None = None) -> ContentTask:
        mode = getattr(payload, "mode", ContentTaskMode.SEARCH)

        if mode == ContentTaskMode.SEARCH:
            if not getattr(payload, "keyword", None):
                raise ValidationException("检索模式下 keyword 不能为空")
            if not getattr(payload, "credential_id", None):
                raise ValidationException("检索模式下 credential_id 不能为空")
        elif mode == ContentTaskMode.DIRECT and not getattr(payload, "direct_content", None):
            raise ValidationException("直投模式下 direct_content 不能为空")

        with transaction.atomic():
            task = ContentTask(
                created_by=user if user and user.is_authenticated else None,
                mode=mode,
                keyword=getattr(payload, "keyword", "") or "",
                case_summary=getattr(payload, "case_summary", "") or "",
                direct_content=getattr(payload, "direct_content", "") or "",
                voice=getattr(payload, "voice", "冰糖") or "冰糖",
                tts_style_prompt=getattr(payload, "tts_style_prompt", "") or "",
                output_mode=getattr(payload, "output_mode", "narration") or "narration",
                discussion_speakers=getattr(payload, "discussion_speakers", []) or [],
                status=ContentTaskStatus.PENDING,
                message=_CREATE_PENDING_MESSAGE,
            )
            if mode == ContentTaskMode.SEARCH and getattr(payload, "credential_id", None):
                from apps.organization.models import AccountCredential

                cred = AccountCredential.objects.filter(id=payload.credential_id, lawyer=user).first()
                if not cred:
                    raise ValidationException("凭证不存在或无权限")
                task.credential = cred
            task.save()

        self.dispatch_task(task=task)
        return task

    def dispatch_task(self, *, task: ContentTask) -> bool:
        try:
            q_task_id = submit_task(
                "apps.content_ops.tasks.execute_content_ops_task",
                str(task.pk),
                task_name=f"content_ops_{task.pk}",
            )
            task.q_task_id = q_task_id
            task.status = ContentTaskStatus.QUEUED
            task.message = _QUEUED_MESSAGE
            task.save(update_fields=["q_task_id", "status", "message", "updated_at"])
            return True
        except Exception as exc:
            logger.exception("Failed to dispatch content_ops task %s", task.pk)
            task.status = ContentTaskStatus.FAILED
            task.message = "任务提交失败"
            task.error = str(exc)
            task.save(update_fields=["status", "message", "error", "updated_at"])
            return False

    def get_task(self, *, task_id: int, user: Any | None = None) -> ContentTask:
        task = ContentTask.objects.select_related("created_by", "credential").filter(id=task_id).first()
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")
        self._check_permission(task, user)
        return task

    def list_tasks(self, *, user: Any | None = None, mode: str | None = None) -> list[ContentTask]:
        qs = ContentTask.objects.select_related("created_by")
        if user and user.is_authenticated:
            qs = qs.filter(created_by=user)
        if mode:
            qs = qs.filter(mode=mode)
        return list(qs[:50])

    def list_articles(self, *, task_id: int, user: Any | None = None) -> list[GeneratedArticle]:
        task = self.get_task(task_id=task_id, user=user)
        return list(GeneratedArticle.objects.filter(task=task).order_by("-created_at"))

    def list_episodes(self, *, task_id: int, user: Any | None = None) -> list[PodcastEpisode]:
        task = self.get_task(task_id=task_id, user=user)
        return list(PodcastEpisode.objects.filter(task=task).order_by("-created_at"))

    def list_discussion_scripts(self, *, task_id: int, user: Any | None = None) -> list[DiscussionScript]:
        task = self.get_task(task_id=task_id, user=user)
        return list(DiscussionScript.objects.filter(task=task).order_by("-created_at"))

    def approve_article(self, *, article_id: int, user: Any | None = None, notes: str = "") -> GeneratedArticle:
        article = self._get_article(article_id)
        article.review_status = ReviewStatus.APPROVED
        article.reviewer_notes = notes
        article.reviewed_by = user if user and user.is_authenticated else None
        article.reviewed_at = timezone.now()
        article.save(update_fields=["review_status", "reviewer_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return article

    def reject_article(self, *, article_id: int, user: Any | None = None, notes: str = "") -> GeneratedArticle:
        article = self._get_article(article_id)
        article.review_status = ReviewStatus.REJECTED
        article.reviewer_notes = notes
        article.reviewed_by = user if user and user.is_authenticated else None
        article.reviewed_at = timezone.now()
        article.save(update_fields=["review_status", "reviewer_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return article

    def update_article(
        self,
        *,
        article_id: int,
        title: str | None = None,
        content: str | None = None,
        user: Any | None = None,
    ) -> GeneratedArticle:
        article = self._get_article(article_id)
        self._check_permission(article.task, user)
        if article.review_status != ReviewStatus.DRAFT:
            raise ValidationException("只能编辑草稿状态的文章")

        update_fields = ["updated_at"]
        if title is not None:
            article.title = title
            update_fields.append("title")
        if content is not None:
            article.content = content
            update_fields.append("content")
        article.save(update_fields=update_fields)
        return article

    def regenerate_article(self, *, article_id: int, user: Any | None = None) -> GeneratedArticle:
        article = self._get_article(article_id)
        self._check_permission(article.task, user)
        task = article.task
        if not task.source_facts:
            raise ValidationException("没有案件事实，无法重新生成")

        from apps.content_ops.services.content_chain import ContentGenerationChain

        chain = ContentGenerationChain()
        result = chain.run(facts=task.source_facts, case_summary=task.case_summary or "")
        article.title = result.title
        article.content = result.content
        article.source_summary = result.summary
        article.llm_model = result.model
        article.token_usage = result.token_usage
        article.review_status = ReviewStatus.DRAFT
        article.reviewer_notes = ""
        article.reviewed_by = None
        article.reviewed_at = None
        article.save()
        return article

    def approve_episode(self, *, episode_id: int, user: Any | None = None, notes: str = "") -> PodcastEpisode:
        episode = self._get_episode(episode_id)
        self._check_permission(episode.task, user)
        episode.review_status = ReviewStatus.APPROVED
        episode.reviewer_notes = notes
        episode.reviewed_by = user if user and user.is_authenticated else None
        episode.reviewed_at = timezone.now()
        episode.save(update_fields=["review_status", "reviewer_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return episode

    def reject_episode(self, *, episode_id: int, user: Any | None = None, notes: str = "") -> PodcastEpisode:
        episode = self._get_episode(episode_id)
        self._check_permission(episode.task, user)
        episode.review_status = ReviewStatus.REJECTED
        episode.reviewer_notes = notes
        episode.reviewed_by = user if user and user.is_authenticated else None
        episode.reviewed_at = timezone.now()
        episode.save(update_fields=["review_status", "reviewer_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return episode

    def retry_task(self, *, task_id: int, user: Any | None = None) -> ContentTask:
        task = self.get_task(task_id=task_id, user=user)
        if task.status != ContentTaskStatus.FAILED:
            raise ValidationException("只能重试失败的任务")

        GeneratedArticle.objects.filter(task=task).delete()
        DiscussionScript.objects.filter(task=task).delete()
        PodcastEpisode.objects.filter(task=task).delete()

        task.status = ContentTaskStatus.PENDING
        task.progress = 0
        task.message = "任务已重新提交"
        task.error = ""
        task.finished_at = None
        task.save()
        self.dispatch_task(task=task)
        return task

    def cancel_task(self, *, task_id: int, user: Any | None = None) -> ContentTask:
        task = self.get_task(task_id=task_id, user=user)
        if task.status not in [ContentTaskStatus.PENDING, ContentTaskStatus.QUEUED, ContentTaskStatus.RUNNING]:
            raise ValidationException("只能取消待执行或运行中的任务")
        task.status = ContentTaskStatus.CANCELLED
        task.message = "任务已取消"
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "message", "finished_at", "updated_at"])
        return task

    def delete_task(self, *, task_id: int, user: Any | None = None) -> None:
        task = self.get_task(task_id=task_id, user=user)
        if task.status in [ContentTaskStatus.RUNNING, ContentTaskStatus.QUEUED]:
            raise ValidationException("不能删除正在执行的任务，请先取消")
        task.delete()

    def get_discussion_script(self, *, script_id: int, user: Any | None = None) -> DiscussionScript:
        script = DiscussionScript.objects.select_related("task").filter(id=script_id).first()
        if not script:
            raise NotFoundError(f"讨论稿 {script_id} 不存在")
        self._check_permission(script.task, user)
        return script

    def update_discussion_turn(
        self,
        *,
        turn_id: int,
        text: str | None = None,
        speaker_style_prompt: str | None = None,
        user: Any | None = None,
    ) -> DiscussionTurn:
        turn = DiscussionTurn.objects.select_related("script__task").filter(id=turn_id).first()
        if not turn:
            raise NotFoundError(f"对话轮次 {turn_id} 不存在")
        self._check_permission(turn.script.task, user)
        if turn.script.review_status != ReviewStatus.DRAFT:
            raise ValidationException("只能编辑草稿状态的讨论稿")

        update_fields = ["updated_at"]
        if text is not None:
            turn.text = text
            update_fields.append("text")
        if speaker_style_prompt is not None:
            turn.speaker_style_prompt = speaker_style_prompt
            update_fields.append("speaker_style_prompt")
        turn.save(update_fields=update_fields)
        return turn

    def approve_discussion_script(
        self,
        *,
        script_id: int,
        user: Any | None = None,
        notes: str = "",
    ) -> DiscussionScript:
        script = self._get_discussion_script(script_id)
        self._check_permission(script.task, user)
        script.review_status = ReviewStatus.APPROVED
        script.reviewer_notes = notes
        script.reviewed_by = user if user and user.is_authenticated else None
        script.reviewed_at = timezone.now()
        script.save(update_fields=["review_status", "reviewer_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return script

    def reject_discussion_script(
        self,
        *,
        script_id: int,
        user: Any | None = None,
        notes: str = "",
    ) -> DiscussionScript:
        script = self._get_discussion_script(script_id)
        self._check_permission(script.task, user)
        script.review_status = ReviewStatus.REJECTED
        script.reviewer_notes = notes
        script.reviewed_by = user if user and user.is_authenticated else None
        script.reviewed_at = timezone.now()
        script.save(update_fields=["review_status", "reviewer_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return script

    def regenerate_discussion_script(self, *, script_id: int, user: Any | None = None) -> DiscussionScript:
        script = self._get_discussion_script(script_id)
        self._check_permission(script.task, user)
        task = script.task
        if not task.source_facts:
            raise ValidationException("没有案件事实，无法重新生成")

        speakers = task.discussion_speakers or []
        if not speakers:
            from apps.content_ops.constants import DEFAULT_DISCUSSION_SPEAKERS

            speakers = DEFAULT_DISCUSSION_SPEAKERS

        from apps.content_ops.services.discussion_chain import DiscussionGenerationChain

        chain = DiscussionGenerationChain()
        result = chain.run(
            facts=task.source_facts,
            speakers=speakers,
            case_summary=task.case_summary or "",
        )

        script.title = result.title
        script.topic = result.topic
        script.llm_model = result.model
        script.token_usage = result.token_usage
        script.review_status = ReviewStatus.DRAFT
        script.reviewer_notes = ""
        script.reviewed_by = None
        script.reviewed_at = None
        script.save()

        script.turns.all().delete()
        style_map = {speaker["name"]: speaker.get("style_prompt", "") for speaker in speakers}
        for idx, turn in enumerate(result.turns):
            DiscussionTurn.objects.create(
                script=script,
                speaker_name=turn["speaker"],
                speaker_style_prompt=style_map.get(turn["speaker"], ""),
                text=turn["text"],
                order=idx,
            )
        return script

    def synthesize_discussion(self, *, script_id: int, user: Any | None = None) -> PodcastEpisode:
        script = self._get_discussion_script(script_id)
        self._check_permission(script.task, user)
        task = script.task

        turns = list(script.turns.order_by("order"))
        if not turns:
            raise ValidationException("讨论稿没有对话轮次")

        turn_dicts = [
            {"text": turn.text, "style_prompt": turn.speaker_style_prompt, "speaker": turn.speaker_name}
            for turn in turns
        ]

        from apps.content_ops.services.tts_service import TTSService

        audio_bytes = TTSService().synthesize_discussion(turns=turn_dicts)
        episode = PodcastEpisode(
            task=task,
            discussion_script=script,
            content_source="discussion",
            voice="multi",
            file_size_bytes=len(audio_bytes),
        )
        episode.audio_file.save(f"discussion_{task.pk}.mp3", ContentFile(audio_bytes))
        episode.save()
        return episode

    @staticmethod
    def _get_article(article_id: int) -> GeneratedArticle:
        article = GeneratedArticle.objects.select_related("task").filter(id=article_id).first()
        if not article:
            raise NotFoundError(f"文章 {article_id} 不存在")
        return article

    @staticmethod
    def _get_episode(episode_id: int) -> PodcastEpisode:
        episode = PodcastEpisode.objects.select_related("task").filter(id=episode_id).first()
        if not episode:
            raise NotFoundError(f"播客单集 {episode_id} 不存在")
        return episode

    @staticmethod
    def _get_discussion_script(script_id: int) -> DiscussionScript:
        script = DiscussionScript.objects.select_related("task").filter(id=script_id).first()
        if not script:
            raise NotFoundError(f"讨论稿 {script_id} 不存在")
        return script

    @staticmethod
    def _check_permission(task: ContentTask, user: Any | None) -> None:
        if user and user.is_authenticated and task.created_by_id and task.created_by_id != user.id:
            raise PermissionDenied("无权访问此任务")
