from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import TeacherProfile, TeacherWallet, TestPurchase, WithdrawalRequest


@staff_member_required
def admin_earnings_view(request):
    paid_purchases = TestPurchase.objects.filter(status=TestPurchase.Status.PAID)

    aggregates = paid_purchases.aggregate(
        gross_kobo=Sum("amount_kobo"),
        teacher_kobo=Sum("teacher_share_kobo"),
        platform_kobo=Sum("platform_share_kobo"),
        fees_kobo=Sum("gateway_fee_kobo"),
        total_count=Count("id"),
    )

    gross_kobo = aggregates["gross_kobo"] or 0
    teacher_kobo = aggregates["teacher_kobo"] or 0
    platform_kobo = aggregates["platform_kobo"] or 0
    fees_kobo = aggregates["fees_kobo"] or 0
    total_sales_count = aggregates["total_count"] or 0
    net_platform_kobo = platform_kobo - fees_kobo

    pending_teachers = TeacherProfile.objects.filter(
        status=TeacherProfile.Status.PENDING
    ).select_related("user").order_by("-created_at")

    pending_withdrawals = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.REQUESTED
    ).select_related("wallet__teacher__user").order_by("-created_at")

    recent_transactions = paid_purchases.select_related(
        "test", "teacher", "buyer"
    ).order_by("-paid_at", "-created_at")[:30]

    active_teachers = TeacherProfile.objects.filter(
        status=TeacherProfile.Status.ACTIVE
    ).select_related("user", "wallet").annotate(
        published_tests_count=Count("tests", filter=Q(tests__is_published=True))
    ).order_by("-created_at")

    context = {
        "gross_naira": Decimal(gross_kobo) / Decimal(100),
        "teacher_naira": Decimal(teacher_kobo) / Decimal(100),
        "platform_naira": Decimal(platform_kobo) / Decimal(100),
        "fees_naira": Decimal(fees_kobo) / Decimal(100),
        "net_platform_naira": Decimal(net_platform_kobo) / Decimal(100),
        "total_sales_count": total_sales_count,
        "pending_teachers": pending_teachers,
        "pending_withdrawals": pending_withdrawals,
        "recent_transactions": recent_transactions,
        "active_teachers": active_teachers,
    }
    return render(request, "monetization/staff_earnings.html", context)


@staff_member_required
@require_POST
def approve_teacher_application(request, teacher_id):
    teacher = get_object_or_404(TeacherProfile, pk=teacher_id)
    teacher.status = TeacherProfile.Status.ACTIVE
    teacher.save(update_fields=["status"])
    TeacherWallet.objects.get_or_create(teacher=teacher)
    messages.success(request, f"Teacher '{teacher.display_name}' has been approved.")
    return redirect("monetization:admin_earnings")


@staff_member_required
@require_POST
def reject_teacher_application(request, teacher_id):
    teacher = get_object_or_404(TeacherProfile, pk=teacher_id)
    teacher.status = TeacherProfile.Status.REJECTED
    teacher.save(update_fields=["status"])
    messages.info(request, f"Teacher application for '{teacher.display_name}' has been rejected.")
    return redirect("monetization:admin_earnings")
