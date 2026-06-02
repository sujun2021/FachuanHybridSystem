from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.cases.admin.caselog_admin import CaseLogAttachmentInline
from apps.cases.models import CaseLog


def test_case_log_attachment_inline_formset_builds_without_removed_fields() -> None:
    inline = CaseLogAttachmentInline(CaseLog, AdminSite())
    request = RequestFactory().get("/admin/cases/caselog/9/change/")
    request.user = AnonymousUser()

    formset = inline.get_formset(request, obj=None)

    assert formset is not None
