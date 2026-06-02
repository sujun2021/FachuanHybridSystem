from apps.automation.admin.sms.court_sms_admin_actions import CourtSMSAdminActions
from apps.automation.models import CourtSMSStatus


def test_should_continue_sms_flow_for_pending_manual_case_binding() -> None:
    assert CourtSMSAdminActions._should_continue_sms_flow(
        previous_status=CourtSMSStatus.PENDING_MANUAL,
        previous_case_id=None,
        new_case_id=2,
    )


def test_should_continue_sms_flow_for_matching_case_binding() -> None:
    assert CourtSMSAdminActions._should_continue_sms_flow(
        previous_status=CourtSMSStatus.MATCHING,
        previous_case_id=None,
        new_case_id=2,
    )


def test_should_not_continue_when_case_already_bound() -> None:
    assert not CourtSMSAdminActions._should_continue_sms_flow(
        previous_status=CourtSMSStatus.MATCHING,
        previous_case_id=2,
        new_case_id=2,
    )


def test_should_not_continue_for_unrelated_status() -> None:
    assert not CourtSMSAdminActions._should_continue_sms_flow(
        previous_status=CourtSMSStatus.COMPLETED,
        previous_case_id=None,
        new_case_id=2,
    )
