from django.urls import path

from .views.checkout import (
    access_paid_purchase,
    check_test_started,
    enter_test,
    paystack_callback,
    purchase_receipt,
    public_test,
    waiting_room,
)
from .views.invitations import accept_invitation, invite_teacher
from .views.staff import (
    admin_earnings_view,
    approve_teacher_application,
    reject_teacher_application,
    staff_mock_export_csv,
    staff_mock_query_api,
    staff_mock_query_view,
)
from .views.teacher import (
    approve_test_start,
    candidate_detail_view,
    create_test,
    dashboard,
    export_test_broadsheet,
    lock_test,
    teacher_onboarding,
    test_leaderboard,
)
from .views.webhooks import paystack_webhook

app_name = "monetization"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("onboarding/", teacher_onboarding, name="teacher_onboarding"),
    path("staff/invitations/", invite_teacher, name="invite_teacher"),
    path("staff/earnings/", admin_earnings_view, name="admin_earnings"),
    path("staff/exams/", staff_mock_query_view, name="staff_mock_query"),
    path("staff/exams/export-csv/", staff_mock_export_csv, name="staff_mock_export_csv"),
    path("staff/api/query-exams/", staff_mock_query_api, name="staff_mock_query_api"),
    path("staff/teachers/<int:teacher_id>/approve/", approve_teacher_application, name="approve_teacher"),
    path("staff/teachers/<int:teacher_id>/reject/", reject_teacher_application, name="reject_teacher"),
    path("invitations/<uuid:invitation_id>/<str:token>/", accept_invitation, name="accept_teacher_invitation"),
    path("tests/new/", create_test, name="create_test"),
    path("tests/<uuid:share_code>/results/", test_leaderboard, name="test_leaderboard"),
    path("tests/<uuid:share_code>/export-csv/", export_test_broadsheet, name="export_test_broadsheet"),
    path("tests/<uuid:share_code>/candidate/<uuid:purchase_id>/", candidate_detail_view, name="candidate_detail"),
    path("tests/<uuid:share_code>/approve/", approve_test_start, name="approve_test_start"),
    path("tests/<uuid:share_code>/lock/", lock_test, name="lock_test"),
    path("tests/<uuid:share_code>/waiting/", waiting_room, name="waiting_room"),
    path("tests/<uuid:share_code>/status/", check_test_started, name="check_test_started"),
    path("tests/<uuid:share_code>/", public_test, name="public_test"),
    path("tests/<uuid:share_code>/enter/", enter_test, name="enter_test"),
    path("paystack/callback/", paystack_callback, name="paystack_callback"),
    path("paystack/webhook/", paystack_webhook, name="paystack_webhook"),
    path("purchases/<uuid:purchase_id>/", purchase_receipt, name="purchase_receipt"),
    path("purchases/<uuid:purchase_id>/start/", access_paid_purchase, name="access_paid_purchase"),
]
