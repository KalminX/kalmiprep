import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Case, Count, DecimalField, F, IntegerField, Q, Sum, Value, When, Window
from django.db.models.functions import Rank
from django.shortcuts import get_object_or_404, redirect, render

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
        .annotate(
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
        )
        .order_by("completed_order", "rank", "buyer_name", "created_at")
    )
    page_obj = Paginator(purchases, 50).get_page(request.GET.get("page", 1))
    return render(request, "monetization/test_leaderboard.html", {
        "test": paid_test,
        "page_obj": page_obj,
    })

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
            paid_test.save()
            form.save_m2m()
            pool = _test_question_pool(paid_test)
            if pool.count() < paid_test.question_count:
                paid_test.delete()
                form.add_error(None, "Selected topics do not contain enough published questions for this test.")
            else:
                if paid_test.randomization == PaidTest.Randomization.SHARED_SET:
                    chosen = random.SystemRandom().sample(list(pool.values_list("pk", flat=True)), paid_test.question_count)
                    paid_test.fixed_question_ids = chosen
                paid_test.is_published = True
                paid_test.save(update_fields=["fixed_question_ids", "is_published"])
                messages.success(request, "Test published. Copy its share link from your teacher dashboard.")
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
