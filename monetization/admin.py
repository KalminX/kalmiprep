from django.contrib import admin, messages
from django.utils import timezone

from .models import (
    PaidTest,
    TeacherProfile,
    TeacherWallet,
    TestPurchase,
    TestRefund,
    TeacherInvitation,
    WalletEntry,
    WebhookReceipt,
    WithdrawalRequest,
)
from .services import PaymentError, mark_withdrawal_paid


@admin.register(TeacherInvitation)
class TeacherInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "kind", "created_at", "expires_at", "accepted_at", "revoked_at")
    list_filter = ("kind", "created_at", "accepted_at", "revoked_at")
    search_fields = ("email", "display_name")
    readonly_fields = tuple(field.name for field in TeacherInvitation._meta.fields)
    has_add_permission = lambda self, request: False
    has_change_permission = lambda self, request, obj=None: False


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "kind", "user", "status", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("display_name", "user__username", "user__email")


@admin.register(PaidTest)
class PaidTestAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "price_kobo", "is_published", "created_at")
    list_filter = ("is_published", "randomization")
    search_fields = ("title", "teacher__display_name")
    readonly_fields = ("share_code", "fixed_question_ids")


@admin.register(TestPurchase)
class TestPurchaseAdmin(admin.ModelAdmin):
    list_display = ("paystack_reference", "test", "buyer_name", "amount_kobo", "teacher_share_kobo", "status", "paid_at")
    list_filter = ("status", "created_at")
    search_fields = ("paystack_reference", "buyer_name", "buyer_email")
    readonly_fields = tuple(field.name for field in TestPurchase._meta.fields)


@admin.register(TeacherWallet)
class TeacherWalletAdmin(admin.ModelAdmin):
    list_display = ("teacher", "balance_kobo", "updated_at")
    readonly_fields = ("teacher", "balance_kobo", "updated_at")


@admin.register(WalletEntry)
class WalletEntryAdmin(admin.ModelAdmin):
    list_display = ("wallet", "kind", "amount_kobo", "source_reference", "created_at")
    readonly_fields = tuple(field.name for field in WalletEntry._meta.fields)


@admin.register(TestRefund)
class TestRefundAdmin(admin.ModelAdmin):
    list_display = ("provider_reference", "purchase", "amount_kobo", "processed_at")
    readonly_fields = tuple(field.name for field in TestRefund._meta.fields)


@admin.register(WebhookReceipt)
class WebhookReceiptAdmin(admin.ModelAdmin):
    list_display = ("event_name", "payload_fingerprint", "received_at")
    readonly_fields = tuple(field.name for field in WebhookReceipt._meta.fields)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("wallet", "amount_kobo", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    readonly_fields = ("wallet", "amount_kobo", "created_at", "reviewed_at", "note")
    actions = ("approve_requests", "reject_requests", "mark_requests_paid")

    @admin.action(description="Approve selected withdrawal requests for manual processing")
    def approve_requests(self, request, queryset):
        count = queryset.filter(status=WithdrawalRequest.Status.REQUESTED).update(
            status=WithdrawalRequest.Status.APPROVED, reviewed_at=timezone.now()
        )
        self.message_user(request, f"Approved {count} request(s). No money was sent.", messages.SUCCESS)

    @admin.action(description="Reject selected withdrawal requests")
    def reject_requests(self, request, queryset):
        count = queryset.filter(status=WithdrawalRequest.Status.REQUESTED).update(
            status=WithdrawalRequest.Status.REJECTED, reviewed_at=timezone.now()
        )
        self.message_user(request, f"Rejected {count} request(s).", messages.SUCCESS)

    @admin.action(description="Mark selected withdrawals paid (records manual payout only)")
    def mark_requests_paid(self, request, queryset):
        paid = errors = 0
        for item in queryset:
            try:
                mark_withdrawal_paid(item.pk)
                paid += 1
            except PaymentError as exc:
                errors += 1
                self.message_user(request, f"Request {item.pk}: {exc}", messages.ERROR)
        if paid:
            self.message_user(request, f"Marked {paid} withdrawal(s) paid and recorded wallet debits. No payout was initiated.", messages.SUCCESS)
        if errors:
            self.message_user(request, f"Could not mark {errors} request(s) paid.", messages.WARNING)
