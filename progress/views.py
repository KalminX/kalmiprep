from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q

from practice.models import PracticeSession, PracticeQuestionResponse
from progress.models import Bookmark, TopicMastery
from curriculum.models import Subject, Topic


def _get_student_filter(request):
    """Returns a Q object matching current user or session_key."""
    if request.user.is_authenticated:
        return Q(user=request.user)
    if not request.session.session_key:
        request.session.create()
    return Q(session_key=request.session.session_key)


def dashboard(request):
    """
    Student diagnostic dashboard.
    Summarizes learning progress, practice history, weak topics, and bookmarked questions.
    """
    filter_q = _get_student_filter(request)

    # Recent practice sessions
    recent_sessions = (
        PracticeSession.objects.filter(filter_q, status=PracticeSession.Status.COMPLETED)
        .select_related("subject", "topic")
        .order_by("-completed_at")[:5]
    )

    # Ongoing active session (if any)
    active_session = (
        PracticeSession.objects.filter(filter_q, status=PracticeSession.Status.IN_PROGRESS)
        .select_related("subject", "topic")
        .order_by("-started_at")
        .first()
    )

    # Aggregate practice stats
    completed_sessions = PracticeSession.objects.filter(filter_q, status=PracticeSession.Status.COMPLETED)
    total_sessions_count = completed_sessions.count()
    total_time_seconds = completed_sessions.aggregate(total_time=Sum("time_spent_seconds"))["total_time"] or 0
    total_time_minutes = int(total_time_seconds / 60)

    # Questions answered & accuracy
    user_responses = PracticeQuestionResponse.objects.filter(
        session__in=completed_sessions
    )
    total_questions_answered = user_responses.count()
    correct_count = user_responses.filter(is_correct=True).count()
    overall_accuracy = int((correct_count / total_questions_answered * 100)) if total_questions_answered > 0 else 0

    # Topic Masteries
    masteries = (
        TopicMastery.objects.filter(filter_q)
        .select_related("topic", "topic__subject")
        .order_by("-last_practiced_at")
    )
    
    weak_topics = [m for m in masteries if m.is_weak_topic][:5]
    strong_topics = [m for m in masteries if m.mastery_percentage >= 80 and m.questions_attempted >= 3][:5]

    # Bookmarks count & recent bookmarks
    bookmarks_qs = (
        Bookmark.objects.filter(filter_q)
        .select_related("question", "question__topic", "question__subject")
        .order_by("-created_at")
    )
    total_bookmarks = bookmarks_qs.count()
    recent_bookmarks = bookmarks_qs[:4]

    # Available subjects for quick-launch
    subjects = Subject.objects.all()

    context = {
        "recent_sessions": recent_sessions,
        "active_session": active_session,
        "total_sessions_count": total_sessions_count,
        "total_time_minutes": total_time_minutes,
        "total_questions_answered": total_questions_answered,
        "overall_accuracy": overall_accuracy,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "masteries": masteries[:8],
        "total_bookmarks": total_bookmarks,
        "recent_bookmarks": recent_bookmarks,
        "subjects": subjects,
    }
    return render(request, "progress/dashboard.html", context)


def bookmarks_list(request):
    """
    Full view of student's bookmarked questions with filtering by subject and study link.
    """
    filter_q = _get_student_filter(request)
    bookmarks_qs = (
        Bookmark.objects.filter(filter_q)
        .select_related("question", "question__subject", "question__topic")
        .prefetch_related("question__options")
        .order_by("-created_at")
    )

    subject_filter = request.GET.get("subject")
    if subject_filter:
        bookmarks_qs = bookmarks_qs.filter(question__subject__slug=subject_filter)

    paginator = Paginator(bookmarks_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    subjects = Subject.objects.all()

    context = {
        "page_obj": page_obj,
        "total_bookmarks": bookmarks_qs.count(),
        "subjects": subjects,
        "current_subject": subject_filter,
    }
    return render(request, "progress/bookmarks.html", context)
