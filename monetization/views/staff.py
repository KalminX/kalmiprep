import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from practice.models import PracticeSession
from ..models import PaidTest, TeacherProfile, TeacherWallet, TestPurchase, WithdrawalRequest


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

    recent_transactions_qs = paid_purchases.select_related(
        "test", "teacher", "buyer"
    ).order_by("-paid_at", "-created_at")

    tx_paginator = Paginator(recent_transactions_qs, 20)
    tx_page_obj = tx_paginator.get_page(request.GET.get("tx_page", 1))

    active_teachers_qs = TeacherProfile.objects.filter(
        status=TeacherProfile.Status.ACTIVE
    ).select_related("user", "wallet").annotate(
        published_tests_count=Count("tests", filter=Q(tests__is_published=True))
    ).order_by("-created_at")

    t_search = request.GET.get("t_search", "").strip()
    if t_search:
        active_teachers_qs = active_teachers_qs.filter(
            Q(display_name__icontains=t_search) | Q(user__email__icontains=t_search)
        )

    t_paginator = Paginator(active_teachers_qs, 15)
    t_page_obj = t_paginator.get_page(request.GET.get("t_page", 1))

    context = {
        "gross_naira": Decimal(gross_kobo) / Decimal(100),
        "teacher_naira": Decimal(teacher_kobo) / Decimal(100),
        "platform_naira": Decimal(platform_kobo) / Decimal(100),
        "fees_naira": Decimal(fees_kobo) / Decimal(100),
        "net_platform_naira": Decimal(net_platform_kobo) / Decimal(100),
        "total_sales_count": total_sales_count,
        "pending_teachers": pending_teachers,
        "pending_withdrawals": pending_withdrawals,
        "recent_transactions": tx_page_obj,
        "tx_page_obj": tx_page_obj,
        "active_teachers": t_page_obj,
        "t_page_obj": t_page_obj,
        "t_search": t_search,
        "total_active_teachers": t_paginator.count,
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


def _filter_mock_query(request):
    queryset = (
        TestPurchase.objects.select_related("test", "teacher", "practice_session", "buyer")
        .prefetch_related("practice_session__responses__question__subject")
        .order_by("-created_at")
    )
    search = request.GET.get("q", "").strip()
    if search:
        queryset = queryset.filter(
            Q(buyer_name__icontains=search)
            | Q(buyer_email__icontains=search)
            | Q(paystack_reference__icontains=search)
            | Q(test__title__icontains=search)
            | Q(teacher__display_name__icontains=search)
        )
    teacher_id = request.GET.get("teacher_id")
    if teacher_id and teacher_id.isdigit():
        queryset = queryset.filter(teacher_id=int(teacher_id))

    test_id = request.GET.get("test_id")
    if test_id and test_id.isdigit():
        queryset = queryset.filter(test_id=int(test_id))

    paper_type = request.GET.get("paper_type", "").strip()
    if paper_type in dict(TestPurchase.PaperType.choices):
        queryset = queryset.filter(paper_type=paper_type)

    exam_structure = request.GET.get("exam_structure", "").strip()
    if exam_structure in dict(PaidTest.ExamStructure.choices):
        queryset = queryset.filter(test__exam_structure=exam_structure)

    status = request.GET.get("status", "").strip()
    if status == "COMPLETED":
        queryset = queryset.filter(practice_session__status=PracticeSession.Status.COMPLETED)
    elif status == "IN_PROGRESS":
        queryset = queryset.filter(practice_session__status=PracticeSession.Status.IN_PROGRESS)
    elif status == "NOT_STARTED":
        queryset = queryset.filter(practice_session__isnull=True)
    elif status == "PAID":
        queryset = queryset.filter(status=TestPurchase.Status.PAID)

    return queryset


def _serialize_purchase(p):
    session = p.practice_session
    utme_400 = session.score_out_of_400 if (session and session.is_completed) else None
    breakdown = []
    if session and session.is_completed:
        for b in session.subject_scores_breakdown:
            breakdown.append({
                "subject": b["subject"].name,
                "score_100": b["score_100"],
                "correct": b["correct"],
                "total": b["total"],
            })
    return {
        "id": str(p.id),
        "candidate_number": p.candidate_number,
        "student_name": p.buyer_name,
        "student_email": p.buyer_email,
        "student_phone": p.buyer_phone,
        "school_name": p.teacher.display_name,
        "school_kind": p.teacher.get_kind_display(),
        "test_title": p.test.title,
        "test_share_code": str(p.test.share_code),
        "exam_structure": p.test.get_exam_structure_display(),
        "paper_type": p.paper_type,
        "paper_type_display": p.get_paper_type_display(),
        "purchase_status": p.status,
        "amount_naira": float(p.amount_naira),
        "session_status": session.get_status_display() if session else "Not Started",
        "is_completed": bool(session and session.is_completed),
        "score": float(session.score) if session else 0.0,
        "total_questions": session.total_questions if session else p.test.question_count,
        "percentage": float(session.percentage) if session else 0.0,
        "utme_score_400": utme_400,
        "subject_breakdown": breakdown,
        "duration_spent": session.formatted_time_spent if session else "--:--",
        "started_at": session.started_at.isoformat() if (session and session.started_at) else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else (
            session.completed_at.isoformat() if (session and session.completed_at) else None
        ),
        "created_at": p.created_at.isoformat(),
        "paystack_reference": p.paystack_reference,
    }


@staff_member_required
def staff_mock_query_view(request):
    queryset = _filter_mock_query(request)
    paginator = Paginator(queryset, 30)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    teachers = TeacherProfile.objects.all().order_by("display_name")
    tests = PaidTest.objects.all().order_by("-created_at")

    context = {
        "page_obj": page_obj,
        "teachers": teachers,
        "tests": tests,
        "paper_type_choices": TestPurchase.PaperType.choices,
        "exam_structures": PaidTest.ExamStructure.choices,
        "filters": {
            "q": request.GET.get("q", ""),
            "teacher_id": request.GET.get("teacher_id", ""),
            "test_id": request.GET.get("test_id", ""),
            "paper_type": request.GET.get("paper_type", ""),
            "exam_structure": request.GET.get("exam_structure", ""),
            "status": request.GET.get("status", ""),
        },
        "total_count": paginator.count,
    }
    return render(request, "monetization/staff_mock_query.html", context)


@staff_member_required
def staff_mock_query_api(request):
    queryset = _filter_mock_query(request)
    limit = min(int(request.GET.get("limit", 100)), 500)
    results = [_serialize_purchase(p) for p in queryset[:limit]]
    return JsonResponse({
        "status": "success",
        "total": queryset.count(),
        "limit": limit,
        "results": results,
    })


@staff_member_required
def staff_mock_export_csv(request):
    queryset = _filter_mock_query(request)
    response = HttpResponse(content_type="text/csv")
    filename = f"all_mock_exams_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Candidate #",
        "Student Name",
        "Email",
        "Phone",
        "School / Institution",
        "Institution Kind",
        "Mock Test Title",
        "Exam Structure",
        "Paper Type",
        "Session Status",
        "Score",
        "Total Questions",
        "Percentage (%)",
        "UTME 400 Aggregate",
        "Subject Breakdown",
        "Duration Spent",
        "Completed At",
        "Payment Reference",
        "Amount (₦)",
    ])

    for p in queryset:
        d = _serialize_purchase(p)
        breakdown_str = " | ".join(
            [f"{b['subject']}: {b['score_100']}% ({b['correct']}/{b['total']})" for b in d["subject_breakdown"]]
        )
        writer.writerow([
            d["candidate_number"] or "",
            d["student_name"],
            d["student_email"],
            d["student_phone"],
            d["school_name"],
            d["school_kind"],
            d["test_title"],
            d["exam_structure"],
            d["paper_type_display"],
            d["session_status"],
            d["score"],
            d["total_questions"],
            f"{d['percentage']}%",
            d["utme_score_400"] or "--",
            breakdown_str,
            d["duration_spent"],
            d["completed_at"] or "--",
            d["paystack_reference"],
            d["amount_naira"],
        ])

    return response
