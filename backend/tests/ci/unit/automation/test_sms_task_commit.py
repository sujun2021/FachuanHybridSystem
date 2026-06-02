from types import SimpleNamespace
from collections.abc import Callable

import pytest

from apps.automation.models import CourtSMSStatus
from apps.automation.services.sms._sms_case_binding_mixin import SMSCaseBindingMixin
from apps.automation.services.sms.court_sms_service import CourtSMSService


class _CommitTaskService(SMSCaseBindingMixin):
    @property
    def case_service(self):  # type: ignore[override]
        return None

    @property
    def lawyer_service(self):  # type: ignore[override]
        return None


def test_submit_task_after_commit_defers_until_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_callbacks: list[Callable[[], None]] = []
    submitted: list[tuple[str, tuple[object, ...], str | None]] = []

    monkeypatch.setattr(
        "apps.automation.services.sms._sms_case_binding_mixin.transaction.on_commit",
        lambda callback: captured_callbacks.append(callback),
    )
    monkeypatch.setattr(
        "apps.core.tasking.submit_task",
        lambda path, *args, task_name=None: submitted.append((path, args, task_name)) or "task-123",
    )

    _CommitTaskService()._submit_task_after_commit(
        "apps.automation.services.sms.court_sms_service.process_sms_from_renaming",
        51,
        task_name="court_sms_continue_51",
        log_message="触发后续处理任务: SMS ID=51, Task ID=%s",
    )

    assert submitted == []
    assert len(captured_callbacks) == 1

    captured_callbacks[0]()

    assert submitted == [
        ("apps.automation.services.sms.court_sms_service.process_sms_from_renaming", (51,), "court_sms_continue_51")
    ]


def test_assign_case_defers_follow_up_task_until_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    service = CourtSMSService()
    sms = SimpleNamespace(
        id=1,
        case_id=None,
        case_log=None,
        scraper_task=None,
        error_message="old",
        status=CourtSMSStatus.PENDING,
        save=lambda *args, **kwargs: None,
    )
    captured_callbacks: list[Callable[[], None]] = []
    submitted: list[tuple[str, tuple[object, ...], str | None]] = []

    monkeypatch.setattr("apps.automation.services.sms.court_sms_service.CourtSMS.objects.get", lambda id: sms)
    monkeypatch.setattr(
        "apps.automation.services.sms._sms_case_binding_mixin.transaction.on_commit",
        lambda callback: captured_callbacks.append(callback),
    )
    monkeypatch.setattr(
        "apps.core.tasking.submit_task",
        lambda path, *args, task_name=None: submitted.append((path, args, task_name)) or "task-456",
    )

    service._case_service = SimpleNamespace(get_case_by_id_internal=lambda case_id: SimpleNamespace(id=case_id))
    service._create_case_binding = lambda sms_obj: True  # type: ignore[method-assign]

    CourtSMSService.assign_case.__wrapped__(service, sms_id=1, case_id=2)

    assert submitted == []
    assert len(captured_callbacks) == 1
    assert sms.case_id == 2
    assert sms.status == CourtSMSStatus.RENAMING

    captured_callbacks[0]()

    assert submitted == [
        ("apps.automation.services.sms.court_sms_service.process_sms_from_renaming", (1,), "court_sms_continue_1")
    ]
