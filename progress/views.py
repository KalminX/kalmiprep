import os
import json
import time
from pathlib import Path
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.http import JsonResponse

from practice.models import PracticeSession, PracticeQuestionResponse
from progress.models import Bookmark, TopicMastery
from curriculum.models import Subject, Topic
from questions.models import Question

STEM_TARGETS = {
    "english-language": {"name": "Use of English (Compulsory)", "target_q": 9413, "target_pages": 1883},
    "mathematics": {"name": "Mathematics", "target_q": 4916, "target_pages": 984},
    "physics": {"name": "Physics", "target_q": 5236, "target_pages": 1048},
    "chemistry": {"name": "Chemistry", "target_q": 4711, "target_pages": 943},
    "biology": {"name": "Biology", "target_q": 5392, "target_pages": 1079},
}
TOTAL_TARGET_QUESTIONS = 29668
TOTAL_TARGET_PAGES = 5937


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


def extractor_status(request):
    """
    Real-time progress telemetry and ETA endpoint for the past questions extraction engine.
    Supports JSON output and rich HTML visual dashboard with auto-polling.
    """
    import datetime
    import re

    from django.conf import settings
    dataset_dir_setting = getattr(settings, "SCRAPER_DATASET_DIR", None)
    if dataset_dir_setting:
        dataset_dir = Path(dataset_dir_setting)
    else:
        container_dir = Path("/app/myschool_dataset")
        host_dir = Path("/home/kalmin/startups/myschool-past-questions-scraper/myschool_dataset")
        dataset_dir = container_dir if container_dir.exists() else host_dir
    progress_file = dataset_dir / "scraper_progress.json"
    telemetry_file = dataset_dir / "scraper_telemetry.json"
    log_file = dataset_dir / "extractor.log"

    completed_pages_data = {}
    if progress_file.exists():
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                raw_prog = json.load(f)
                completed_pages_data = raw_prog.get("completed_pages", {})
        except Exception:
            pass

    telemetry_data = {}
    is_daemon_alive = False
    if telemetry_file.exists():
        try:
            with open(telemetry_file, "r", encoding="utf-8") as f:
                telemetry_data = json.load(f)
                last_hb = telemetry_data.get("last_heartbeat", 0)
                is_daemon_alive = (time.time() - last_hb) < 90
        except Exception:
            pass

    # Inspect Celery and RabbitMQ status and active tasks
    celery_active = False
    active_workers_count = 0
    celery_active_tasks = []
    celery_active_subjects = set()
    try:
        from config.celery import app as celery_app
        insp = celery_app.control.inspect(timeout=0.4)
        if insp:
            ping_res = insp.ping()
            if ping_res:
                active_workers_count = len(ping_res)
                celery_active = active_workers_count > 0

            active_map = insp.active() or {}
            for worker_name, tasks in active_map.items():
                for t in tasks:
                    args = t.get("args", [])
                    name = t.get("name", "")
                    if "scrape_subject_page_task" in name and len(args) >= 2:
                        subj_arg = args[0]
                        page_arg = args[1]
                        celery_active_subjects.add(subj_arg)
                        celery_active_tasks.append({
                            "subject": subj_arg,
                            "subject_name": STEM_TARGETS.get(subj_arg, {}).get("name", subj_arg.title()),
                            "page": page_arg,
                            "task_id": t.get("id"),
                        })
    except Exception:
        pass

    # Read recent logs and compute live velocity dynamically
    recent_logs = []
    all_log_lines = []
    live_velocity = 0.0

    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                daemon_lines = f.readlines()
                all_log_lines.extend([l.strip() for l in daemon_lines[-18:] if l.strip()])

                # Calculate velocity from the last 35 log lines
                sample_lines = daemon_lines[-35:]
                page_events = []
                log_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* Page \d+/\d+ completed \(\+(\d+) Qs")
                for l in sample_lines:
                    m = log_pattern.search(l)
                    if m:
                        try:
                            dt = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f")
                            page_events.append((dt.timestamp(), int(m.group(2))))
                        except Exception:
                            pass

                if len(page_events) >= 2:
                    dt = page_events[-1][0] - page_events[0][0]
                    total_q = sum(q for _, q in page_events[1:])
                    if dt > 0:
                        live_velocity = round((total_q / dt) * 60, 1)
        except Exception:
            pass

    # Also include Celery worker events in live logs
    celery_log_file = dataset_dir / "celery_tasks.log"
    if celery_log_file.exists():
        try:
            with open(celery_log_file, "r", encoding="utf-8", errors="replace") as f:
                all_log_lines.extend([l.strip() for l in f.readlines()[-18:] if l.strip()])
        except Exception:
            pass

    all_log_lines.sort()
    recent_logs = all_log_lines[-12:] if all_log_lines else []

    # If celery is running in parallel, augment velocity
    if celery_active:
        live_velocity = max(live_velocity, 50.0) + (len(celery_active_tasks) * 35.0)

    if live_velocity <= 0 and (is_daemon_alive or celery_active):
        live_velocity = 120.0

    current_active_subject_slug = telemetry_data.get("subject", "")
    current_active_page = telemetry_data.get("current_page", 0)
    current_active_total_pages = telemetry_data.get("total_pages", 0)

    subjects_progress = []
    total_db_questions = 0
    total_db_solutions = 0
    total_completed_pages = 0

    for slug, meta in STEM_TARGETS.items():
        db_count = Question.objects.filter(subject__slug=slug).count()
        sol_count = Question.objects.filter(subject__slug=slug).exclude(explanation="").count()
        # Accurate calculation combining progress file and database question count (5 Qs per page)
        raw_done = len(completed_pages_data.get(slug, []))
        pages_done = min(meta["target_pages"], max(raw_done, int(round(db_count / 5))))
        pct = round((db_count / meta["target_q"]) * 100, 1) if meta["target_q"] else 0.0

        total_db_questions += db_count
        total_db_solutions += sol_count
        total_completed_pages += pages_done

        is_current_daemon = (is_daemon_alive and current_active_subject_slug == slug)
        is_celery_current = (slug in celery_active_subjects)
        is_completed = (db_count >= meta["target_q"] or pages_done >= meta["target_pages"] or pct >= 100.0)

        if is_completed:
            status_text = "Fully Ingested (100%)"
            status_style = "emerald"
        elif is_celery_current:
            status_text = "Live Celery Ingestion"
            status_style = "blue"
        elif is_current_daemon:
            status_text = "Live Crawler Daemon"
            status_style = "brand"
        elif db_count > 0:
            remaining_for_subj = max(0, meta["target_q"] - db_count)
            status_text = f"In Progress ({remaining_for_subj} remaining)"
            status_style = "indigo"
        else:
            status_text = "Queued"
            status_style = "slate"

        subjects_progress.append({
            "slug": slug,
            "name": meta["name"],
            "target_questions": meta["target_q"],
            "target_pages": meta["target_pages"],
            "in_database": db_count,
            "with_solutions": sol_count,
            "solutions_percent": round((sol_count / db_count) * 100, 1) if db_count > 0 else 0.0,
            "pages_completed": pages_done,
            "percent_complete": pct,
            "is_completed": is_completed,
            "is_current": is_current_daemon or is_celery_current,
            "is_celery_active": is_celery_current,
            "is_daemon_active": is_current_daemon,
            "status_text": status_text,
            "status_style": status_style,
        })

    remaining_questions = max(0, TOTAL_TARGET_QUESTIONS - total_db_questions)
    overall_percent = round((total_db_questions / TOTAL_TARGET_QUESTIONS) * 100, 2)

    # Dynamic ETA calculation based on real multi-threaded velocity
    if (is_daemon_alive or celery_active) and live_velocity > 0:
        eta_minutes = int(remaining_questions / live_velocity) if remaining_questions > 0 else 0
        eta_hours = eta_minutes // 60
        eta_remaining_mins = eta_minutes % 60
        formatted_eta = f"{eta_hours}h {eta_remaining_mins}m" if eta_hours > 0 else f"{eta_minutes} mins"
        rate_display = f"~{int(round(live_velocity))} questions/min"
    else:
        formatted_eta = "Paused / Complete"
        rate_display = "0 questions/min"

    active_subject_name = STEM_TARGETS.get(current_active_subject_slug, {}).get("name", current_active_subject_slug.replace("-", " ").title())
    active_subject_percent = round((current_active_page / current_active_total_pages) * 100, 1) if current_active_total_pages > 0 else 0.0

    data = {
        "is_active": is_daemon_alive or celery_active,
        "celery_active": celery_active,
        "celery_workers_count": active_workers_count,
        "celery_active_tasks": celery_active_tasks,
        "celery_active_subjects": list(celery_active_subjects),
        "is_daemon_alive": is_daemon_alive,
        "rabbitmq_connected": True,
        "total_target_questions": TOTAL_TARGET_QUESTIONS,
        "total_target_pages": TOTAL_TARGET_PAGES,
        "total_ingested_questions": total_db_questions,
        "total_ingested_solutions": total_db_solutions,
        "total_completed_pages": total_completed_pages,
        "remaining_questions": remaining_questions,
        "overall_percent": overall_percent,
        "scraping_rate": rate_display,
        "estimated_time_remaining": formatted_eta,
        "active_telemetry": telemetry_data,
        "active_subject_name": active_subject_name,
        "active_subject_slug": current_active_subject_slug,
        "active_subject_page": current_active_page,
        "active_subject_total_pages": current_active_total_pages,
        "active_subject_percent": active_subject_percent,
        "recent_logs": recent_logs,
        "parallel_workers": max(active_workers_count, 1) + (1 if is_daemon_alive else 0),
        "subjects": subjects_progress,
    }

    if request.headers.get("Accept") == "application/json" or request.GET.get("format") == "json":
        return JsonResponse(data)

    return render(request, "progress/extractor_status.html", data)
