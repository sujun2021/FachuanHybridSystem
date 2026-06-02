from types import SimpleNamespace

from apps.automation.models import ScraperTaskStatus
from apps.automation.services.sms._sms_download_mixin import SMSDownloadMixin


class DownloadWaitService(SMSDownloadMixin):
    pass


def test_waits_for_pending_download_even_when_party_names_exist() -> None:
    service = DownloadWaitService()
    sms = SimpleNamespace(
        id=2,
        party_names=["张三"],
        download_links=["https://example.test/document"],
        scraper_task=object(),
    )
    pending_task = SimpleNamespace(status=ScraperTaskStatus.PENDING)

    service._refresh_scraper_task = lambda _sms: pending_task  # type: ignore[method-assign]

    assert service._should_wait_for_document_download(sms) is True


def test_does_not_wait_without_download_link() -> None:
    service = DownloadWaitService()
    sms = SimpleNamespace(id=2, party_names=["张三"], download_links=[], scraper_task=object())

    assert service._should_wait_for_document_download(sms) is False
