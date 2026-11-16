import csv
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Case, Count, DecimalField, F, IntegerField, Q, Sum, Value, When, Window
from django.db.models.functions import Rank
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from curriculum.models import Subject
from practice.models import PracticeSession
from questions.models import Question

from ..forms import PaidTestForm, TeacherApplicationForm, WithdrawalForm
from ..models import PaidTest, TeacherProfile, TeacherWallet, TestPurchase, WithdrawalRequest
from ..services import PaymentError, request_withdrawal

@login_required
def dashboard(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if request.method == "POST" and not teacher:
        form = TeacherApplicationForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)
            teacher.user = request.user
            teacher.save()
            messages.success(request, "Your teacher account request is submitted for review.")
            return redirect("monetization:dashboard")
    else:
        form = TeacherApplicationForm()

    wallet = None
    withdrawal_form = None
    if teacher and teacher.status == TeacherProfile.Status.ACTIVE:
        wallet, _ = TeacherWallet.objects.get_or_create(teacher=teacher)
        if request.method == "POST" and request.POST.get("action") == "withdraw":
            withdrawal_form = WithdrawalForm(request.POST, wallet=wallet)
            if withdrawal_form.is_valid():
                try:
                    request_withdrawal(wallet, withdrawal_form.cleaned_data["amount_naira"])
                except PaymentError as exc:
                    withdrawal_form.add_error(None, str(exc))
                else:
                    messages.success(request, "Withdrawal request recorded for manual review. No payout has been sent.")
                    return redirect("monetization:dashboard")
        else:
            withdrawal_form = WithdrawalForm(wallet=wallet)
    tests = teacher.tests.annotate(
        sales_count=Count(
            "purchases",
            filter=Q(purchases__status__in=[TestPurchase.Status.PAID, TestPurchase.Status.PARTIALLY_REFUNDED]),
        )
    ).order_by("-created_at") if teacher else []
    context = {
        "teacher": teacher,
        "application_form": form,
        "wallet": wallet,
        "wallet_balance_naira": wallet.balance_kobo / 100 if wallet else 0,
        "available_kobo": _available_balance(wallet) if wallet else 0,
        "available_naira": _available_balance(wallet) / 100 if wallet else 0,
        "withdrawal_form": withdrawal_form,
        "withdrawals": wallet.withdrawals.all()[:10] if wallet else [],
        "wallet_entries": wallet.entries.select_related("purchase", "purchase__test")[:10] if wallet else [],
        "tests": tests,
        "classroom_count": teacher.classrooms.count() if teacher else 0,
    }
    return render(request, "monetization/dashboard.html", context)


@login_required
def teacher_onboarding(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not teacher or teacher.status != TeacherProfile.Status.ACTIVE:
        return redirect("monetization:dashboard")
    classes = teacher.classrooms.prefetch_related("assignments")
    has_class = classes.exists()
    has_assignment = any(classroom.assignments.exists() for classroom in classes)
    return render(request, "monetization/teacher_onboarding.html", {
        "teacher": teacher,
        "has_class": has_class,
        "has_assignment": has_assignment,
        "classrooms_url": "classrooms:index",
        "tutorial_url": settings.TEACHER_TUTORIAL_URL,
    })

def _available_balance(wallet):
    if not wallet:
        return 0
    reserved = wallet.withdrawals.filter(status__in=[WithdrawalRequest.Status.REQUESTED, WithdrawalRequest.Status.APPROVED]).aggregate(
        total=Sum("amount_kobo")
    )["total"] or 0
    return max(wallet.balance_kobo - reserved, 0)

@login_required
def test_leaderboard(request, share_code):
    paid_test = get_object_or_404(
        PaidTest.objects.select_related("teacher"),
        share_code=share_code,
        teacher__user=request.user,
    )
    purchases = (
        TestPurchase.objects.filter(
            test=paid_test,
            status__in=[
                TestPurchase.Status.PAID,
                TestPurchase.Status.PARTIALLY_REFUNDED,
                TestPurchase.Status.REFUNDED,
            ],
        )
        .select_related("practice_session")
    )

    paper_type_filter = request.GET.get("paper_type", "").strip()
    if paper_type_filter in dict(TestPurchase.PaperType.choices):
        purchases = purchases.filter(paper_type=paper_type_filter)

    search_query = request.GET.get("q", "").strip()
    if search_query:
        purchases = purchases.filter(
            Q(buyer_name__icontains=search_query)
            | Q(buyer_email__icontains=search_query)
            | Q(paystack_reference__icontains=search_query)
        )

    purchases = purchases.annotate(
        rank_score=Case(
            When(
                practice_session__status=PracticeSession.Status.COMPLETED,
                then=F("practice_session__percentage"),
            ),
            default=Value(None),
            output_field=DecimalField(max_digits=5, decimal_places=2),
        ),
        rank=Window(
            expression=Rank(),
            order_by=F("rank_score").desc(nulls_last=True),
        ),
        correct_count=Count(
            "practice_session__responses",
            filter=Q(practice_session__responses__is_correct=True),
        ),
        completed_order=Case(
            When(practice_session__status=PracticeSession.Status.COMPLETED, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
    ).order_by("completed_order", "rank", "candidate_number", "buyer_name", "created_at")

    page_obj = Paginator(purchases, 50).get_page(request.GET.get("page", 1))
    
    # Realtime situational metrics for the proctor room
    base_purchases = paid_test.purchases.filter(
        status__in=[
            TestPurchase.Status.PAID,
            TestPurchase.Status.PARTIALLY_REFUNDED,
            TestPurchase.Status.REFUNDED,
        ]
    )
    proctor_stats = {
        "total": base_purchases.count(),
        "waiting": base_purchases.filter(practice_session__isnull=True).count(),
        "active": base_purchases.filter(practice_session__status=PracticeSession.Status.IN_PROGRESS).count(),
        "completed": base_purchases.filter(practice_session__status=PracticeSession.Status.COMPLETED).count(),
    }

    return render(request, "monetization/test_leaderboard.html", {
        "test": paid_test,
        "page_obj": page_obj,
        "paper_type_filter": paper_type_filter,
        "search_query": search_query,
        "paper_type_choices": TestPurchase.PaperType.choices,
        "proctor_stats": proctor_stats,
    })


@login_required
def export_test_broadsheet(request, share_code):
    paid_test = get_object_or_404(
        PaidTest.objects.select_related("teacher"),
        share_code=share_code,
        teacher__user=request.user,
    )
    purchases = (
        TestPurchase.objects.filter(
            test=paid_test,
            status__in=[
                TestPurchase.Status.PAID,
                TestPurchase.Status.PARTIALLY_REFUNDED,
                TestPurchase.Status.REFUNDED,
            ],
        )
        .select_related("practice_session")
        .order_by("candidate_number", "created_at")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"broadsheet_{paid_test.title.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Candidate #",
        "Student Name",
        "Email",
        "Phone",
        "Paper Type",
        "Status",
        "Score",
        "Total Questions",
        "Percentage (%)",
        "UTME 400 Aggregate",
        "Subject Scores Breakdown",
        "Duration Spent",
        "Completed At",
        "Payment Reference",
    ])

    for p in purchases:
        session = p.practice_session
        status_disp = session.get_status_display() if session else "Not Started"
        score_val = str(session.score) if session else "0"
        total_q = session.total_questions if session else paid_test.question_count
        pct = f"{session.percentage}%" if session else "0%"
        utme_400 = str(session.score_out_of_400) if (session and session.is_completed) else "--"

        breakdown_str = ""
        if session and session.is_completed:
            parts = []
            for b in session.subject_scores_breakdown:
                parts.append(f"{b['subject'].name}: {b['score_100']}% ({b['correct']}/{b['total']})")
            breakdown_str = " | ".join(parts)

        duration = session.formatted_time_spent if session else "--:--"
        completed_time = p.completed_at.strftime("%Y-%m-%d %H:%M") if p.completed_at else (
            session.completed_at.strftime("%Y-%m-%d %H:%M") if (session and session.completed_at) else "--"
        )

        writer.writerow([
            p.candidate_number or "",
            p.buyer_name,
            p.buyer_email,
            p.buyer_phone,
            p.get_paper_type_display(),
            status_disp,
            score_val,
            total_q,
            pct,
            utme_400,
            breakdown_str,
            duration,
            completed_time,
            p.paystack_reference,
        ])

    return response


@login_required
def candidate_detail_view(request, share_code, purchase_id):
    paid_test = get_object_or_404(
        PaidTest,
        share_code=share_code,
        teacher__user=request.user,
    )
    purchase = get_object_or_404(
        TestPurchase.objects.select_related("practice_session", "teacher"),
        pk=purchase_id,
        test=paid_test,
    )
    session = purchase.practice_session
    responses = []
    subjects_map = {}
    stats = {"total": 0, "correct": 0, "incorrect": 0, "unanswered": 0}

    if session:
        responses = list(
            session.responses.select_related("question", "question__subject", "question__topic", "selected_option")
            .prefetch_related("question__options")
            .order_by("order")
        )
        stats["total"] = len(responses)
        for r in responses:
            s_obj = r.question.subject
            if s_obj:
                subjects_map.setdefault(s_obj.slug, {"name": s_obj.name, "count": 0, "slug": s_obj.slug})
                subjects_map[s_obj.slug]["count"] += 1
            if r.selected_option and r.is_correct:
                stats["correct"] += 1
            elif r.selected_option:
                stats["incorrect"] += 1
            else:
                stats["unanswered"] += 1

    return render(request, "monetization/candidate_detail.html", {
        "test": paid_test,
        "purchase": purchase,
        "session": session,
        "responses": responses,
        "subjects_list": list(subjects_map.values()),
        "stats": stats,
    })


def _build_paid_test_questions(paid_test, request_post=None):
    """
    Selects questions and constructs the blueprint configuration and fixed_question_ids
    based on the exam structure (Single Subject, Custom Multi-Subject, or JAMB UTME).
    Returns (success: bool, error_message: str).
    """
    selected_topics = list(paid_test.topics.select_related("subject").all())
    if not selected_topics:
        return False, "Please select at least one topic for this test."

    subject_topics = {}
    for t in selected_topics:
        subject_topics.setdefault(t.subject, []).append(t)

    is_multi_subject = paid_test.exam_structure in [
        PaidTest.ExamStructure.CUSTOM_MULTI_SUBJECT,
        PaidTest.ExamStructure.JAMB_UTME_STANDARD,
    ]

    if not is_multi_subject or len(subject_topics) <= 1:
        pool = _test_question_pool(paid_test)
        if pool.count() < paid_test.question_count:
            return False, f"Selected topics contain only {pool.count()} published questions, but {paid_test.question_count} are required."
        if paid_test.randomization == PaidTest.Randomization.SHARED_SET:
            paid_test.fixed_question_ids = random.SystemRandom().sample(
                list(pool.values_list("pk", flat=True)), paid_test.question_count
            )
        first_subject = selected_topics[0].subject
        paid_test.blueprint_config = {
            "subjects": [
                {
                    "subject_id": first_subject.id,
                    "subject_name": first_subject.name,
                    "question_count": paid_test.question_count,
                }
            ]
        }
        return True, ""

    subjects_list = list(subject_topics.keys())
    quotas = {}

    if paid_test.exam_structure == PaidTest.ExamStructure.JAMB_UTME_STANDARD:
        total_needed = 0
        for subj in subjects_list:
            if "english" in subj.name.lower():
                quotas[subj.id] = 60
            else:
                quotas[subj.id] = 40
            total_needed += quotas[subj.id]
        paid_test.question_count = total_needed
        if not paid_test.time_limit_minutes or paid_test.time_limit_minutes == 30:
            paid_test.time_limit_minutes = 120
    else:
        has_custom_quotas = False
        if request_post:
            for subj in subjects_list:
                key = f"subject_quota_{subj.id}"
                if key in request_post and request_post[key].isdigit():
                    quotas[subj.id] = int(request_post[key])
                    has_custom_quotas = True

        if not has_custom_quotas:
            base_count = paid_test.question_count // len(subjects_list)
            remainder = paid_test.question_count % len(subjects_list)
            for idx, subj in enumerate(subjects_list):
                quotas[subj.id] = base_count + (1 if idx < remainder else 0)

    all_fixed_ids = []
    blueprint_subjects = []

    for subj in subjects_list:
        needed = quotas.get(subj.id, 0)
        if needed <= 0:
            continue
        subj_pool = (
            Question.objects.filter(subject=subj, topic__in=subject_topics[subj], is_published=True)
            .annotate(option_count=Count("options"), correct_count=Count("options", filter=Q(options__is_correct=True)))
            .filter(option_count__gte=2, correct_count=1)
            .distinct()
        )
        avail = subj_pool.count()
        if avail < needed:
            return False, f"Subject '{subj.name}' has only {avail} valid published questions, but {needed} were requested."

        drawn_ids = random.SystemRandom().sample(list(subj_pool.values_list("pk", flat=True)), needed)
        all_fixed_ids.extend(drawn_ids)
        blueprint_subjects.append({
            "subject_id": subj.id,
            "subject_name": subj.name,
            "question_count": needed,
        })

    paid_test.question_count = len(all_fixed_ids)
    paid_test.fixed_question_ids = all_fixed_ids
    paid_test.blueprint_config = {"subjects": blueprint_subjects}
    return True, ""


@login_required
def create_test(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not teacher or teacher.status != TeacherProfile.Status.ACTIVE:
        messages.warning(request, "An approved teacher account is required to publish tests. Apply below or sign in as demo_teacher.")
        return redirect("monetization:dashboard")
    if request.method == "POST":
        form = PaidTestForm(request.POST)
        if form.is_valid():
            paid_test = form.save(commit=False)
            paid_test.teacher = teacher
            if not paid_test.blueprint_config:
                paid_test.blueprint_config = {}
            paid_test.save()
            form.save_m2m()

            success, err_msg = _build_paid_test_questions(paid_test, request.POST)
            if not success:
                paid_test.delete()
                form.add_error(None, err_msg)
            else:
                paid_test.is_published = True
                paid_test.save(update_fields=["fixed_question_ids", "blueprint_config", "question_count", "time_limit_minutes", "is_published"])
                messages.success(request, f"Mock Exam '{paid_test.title}' published successfully.")
                return redirect("monetization:dashboard")
    else:
        form = PaidTestForm()
    return render(request, "monetization/test_form.html", {"form": form})

def _test_question_pool(paid_test):
    return (
        Question.objects.filter(topic__in=paid_test.topics.all(), is_published=True)
        .annotate(option_count=Count("options"), correct_count=Count("options", filter=Q(options__is_correct=True)))
        .filter(option_count__gte=2, correct_count=1)
        .distinct()
    )


@login_required
def approve_test_start(request, share_code):
    paid_test = get_object_or_404(
        PaidTest,
        share_code=share_code,
        teacher__user=request.user,
    )
    if request.method == "POST":
        paid_test.is_approved_for_start = True
        paid_test.save(update_fields=["is_approved_for_start"])
        messages.success(request, f"Exam '{paid_test.title}' is now unlocked. All waiting students can begin.")
    return redirect("monetization:test_leaderboard", share_code=share_code)


@login_required
def lock_test(request, share_code):
    paid_test = get_object_or_404(
        PaidTest,
        share_code=share_code,
        teacher__user=request.user,
    )
    if request.method == "POST":
        paid_test.is_approved_for_start = False
        paid_test.save(update_fields=["is_approved_for_start"])
        messages.info(request, f"Exam '{paid_test.title}' is now locked. New attempts are paused.")
    return redirect("monetization:test_leaderboard", share_code=share_code)
