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
from .views.staff import admin_earnings_view, approve_teacher_application, reject_teacher_application
from .views.teacher import (
    approve_test_start,
    create_test,
    dashboard,
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
    path("staff/teachers/<int:teacher_id>/approve/", approve_teacher_application, name="approve_teacher"),
    path("staff/teachers/<int:teacher_id>/reject/", reject_teacher_application, name="reject_teacher"),
    path("invitations/<uuid:invitation_id>/<str:token>/", accept_invitation, name="accept_teacher_invitation"),
    path("tests/new/", create_test, name="create_test"),
    path("tests/<uuid:share_code>/results/", test_leaderboard, name="test_leaderboard"),
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
