import random
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count, Q

from curriculum.models import Subject, Topic
from questions.models import Question, Option
from practice.models import PracticeSession, PracticeQuestionResponse
from progress.models import TopicMastery


def practice_setup(request):
    """
    Setup wizard for launching Topic Practice, Timed Assessments, or CBT Mocks.
    """
    subjects = Subject.objects.filter(is_active=True).prefetch_related("topics")
    
    if request.method == "POST":
        subject_id = request.POST.get("subject")
        topic_id = request.POST.get("topic")
        mode = request.POST.get("mode", PracticeSession.Mode.TOPIC_PRACTICE)
        question_count = int(request.POST.get("question_count", 10))
        exam_type = request.POST.get("exam_type", "")

        subject = get_object_or_404(Subject, pk=subject_id)
        topic = Topic.objects.filter(pk=topic_id).first() if topic_id else None

        # Build query for questions
        q_filter = Q(subject=subject, is_published=True)
        if topic:
            q_filter &= Q(topic=topic)
        if exam_type:
            q_filter &= Q(exam_type=exam_type)

        available_questions = list(Question.objects.filter(q_filter).values_list("id", flat=True))
        
        # If not enough in topic, fallback to subject
        if len(available_questions) < question_count and topic:
            fallback = list(Question.objects.filter(subject=subject, is_published=True).values_list("id", flat=True))
            available_questions = list(set(available_questions + fallback))

        if not available_questions:
            messages.error(request, "No questions found matching your selected criteria. Try selecting 'All Topics'.")
            return redirect("practice:setup")

        # Pick random questions
        selected_ids = random.sample(available_questions, min(len(available_questions), question_count))
        
        # Determine time limit
        time_limit = 0
        if mode in [PracticeSession.Mode.TIMED_TEST, PracticeSession.Mode.CBT_MOCK]:
            # Default 1.2 minutes per question
            time_limit = len(selected_ids) * 72

        # Create session
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        title = f"{subject.name}"
        if topic:
            title += f" — {topic.name}"
        else:
            title += " Comprehensive Mock"

        practice_session = PracticeSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            mode=mode,
            title=title,
            subject=subject,
            topic=topic,
            exam_type=exam_type if exam_type else None,
            total_questions=len(selected_ids),
            time_limit_seconds=time_limit,
            status=PracticeSession.Status.IN_PROGRESS,
        )

        # Create Question Response entries
        for idx, qid in enumerate(selected_ids, start=1):
            PracticeQuestionResponse.objects.create(
                session=practice_session,
                question_id=qid,
                order=idx,
            )

        return redirect("practice:session_view", session_id=practice_session.id)

    # Pre-select subject/topic if passed via GET
    pre_subject = request.GET.get("subject", "")
    pre_topic = request.GET.get("topic", "")
    pre_mode = request.GET.get("mode", PracticeSession.Mode.TOPIC_PRACTICE)

    context = {
        "subjects": subjects,
        "pre_subject": pre_subject,
        "pre_topic": pre_topic,
        "pre_mode": pre_mode,
        "modes": PracticeSession.Mode.choices,
        "exam_choices": Question.ExamType.choices,
    }
    return render(request, "practice/practice_setup.html", context)


def session_view(request, session_id):
    """
    Renders the active practice or CBT examination environment.
    """
    session = get_object_or_404(
        PracticeSession.objects.select_related("subject", "topic"),
        pk=session_id,
    )

    if session.status == PracticeSession.Status.COMPLETED:
        return redirect("practice:session_results", session_id=session.id)

    responses = (
        session.responses.all()
        .select_related("question", "question__topic", "selected_option")
        .prefetch_related("question__options")
        .order_by("order")
    )

    # Current question index
    q_index = int(request.GET.get("q", 1))
    if q_index < 1 or q_index > responses.count():
        q_index = 1

    current_resp = responses[q_index - 1]

    context = {
        "session": session,
        "responses": responses,
        "current_resp": current_resp,
        "current_index": q_index,
        "total_count": responses.count(),
        "prev_index": q_index - 1 if q_index > 1 else None,
        "next_index": q_index + 1 if q_index < responses.count() else None,
    }

    if session.mode == PracticeSession.Mode.TOPIC_PRACTICE:
        return render(request, "practice/topic_practice.html", context)
    else:
        return render(request, "practice/cbt_exam.html", context)


@require_POST
def submit_answer(request, session_id, response_id):
    """
    Handles student answer submission for a specific question in a session.
    """
    session = get_object_or_404(PracticeSession, pk=session_id)
    resp = get_object_or_404(PracticeQuestionResponse, pk=response_id, session=session)

    option_id = request.POST.get("option_id")
    is_flagged = request.POST.get("is_flagged") == "true"
    time_spent = int(request.POST.get("time_spent", 0))

    if option_id:
        selected_opt = Option.objects.filter(pk=option_id, question=resp.question).first()
        resp.selected_option = selected_opt
        resp.is_correct = selected_opt.is_correct if selected_opt else False
        resp.answered_at = timezone.now()

    resp.is_flagged = is_flagged
    resp.time_spent_seconds += time_spent
    resp.save()

    # If instant practice mode, render feedback partial
    if session.mode == PracticeSession.Mode.TOPIC_PRACTICE:
        current_index = int(request.POST.get("current_index", 1))
        total_count = session.total_questions
        next_index = current_index + 1 if current_index < total_count else None
        
        return render(
            request,
            "practice/partials/question_feedback.html",
            {
                "session": session,
                "resp": resp,
                "current_index": current_index,
                "next_index": next_index,
                "total_count": total_count,
            },
        )

    # For CBT Mock, return JSON or small status badge
    return render(
        request,
        "practice/partials/cbt_grid_item.html",
        {
            "resp": resp,
            "order": resp.order,
            "is_current": True,
        },
    )


@require_POST
def finish_session(request, session_id):
    """
    Finalizes an assessment, runs server-side scoring, records topic diagnostics, and shows results.
    """
    session = get_object_or_404(PracticeSession, pk=session_id)
    time_spent = int(request.POST.get("total_time_spent", session.time_spent_seconds or 0))
    session.time_spent_seconds = time_spent

    # Calculate results
    session.calculate_results()

    # Update Topic Mastery diagnostics
    for resp in session.responses.select_related("question__topic"):
        topic = resp.question.topic
        if topic:
            if session.user:
                mastery, _ = TopicMastery.objects.get_or_create(user=session.user, topic=topic)
            else:
                mastery, _ = TopicMastery.objects.get_or_create(session_key=session.session_key, topic=topic)
            
            mastery.questions_attempted += 1
            if resp.is_correct:
                mastery.questions_correct += 1
            mastery.save()

    return redirect("practice:session_results", session_id=session.id)


def session_results(request, session_id):
    """
    Performance Summary & Diagnostics view.
    Displays overall score, topic breakdown, question review, and targeted practice recommendations.
    """
    session = get_object_or_404(
        PracticeSession.objects.select_related("subject", "topic"),
        pk=session_id,
    )

    responses = (
        session.responses.all()
        .select_related("question", "question__topic", "selected_option")
        .prefetch_related("question__options")
        .order_by("order")
    )

    # Performance Grade Classification
    pct = session.percentage
    if pct >= 80:
        grade = "Mastery / Distinction"
        grade_color = "emerald"
    elif pct >= 60:
        grade = "Proficient / Credit"
        grade_color = "blue"
    elif pct >= 45:
        grade = "Moderate / Pass"
        grade_color = "amber"
    else:
        grade = "Needs Focused Revision"
        grade_color = "rose"

    # Topic Performance Breakdown
    topic_scores = {}
    for r in responses:
        tname = r.question.topic.name if r.question.topic else "General Topics"
        if tname not in topic_scores:
            topic_scores[tname] = {"attempted": 0, "correct": 0, "topic": r.question.topic}
        topic_scores[tname]["attempted"] += 1
        if r.is_correct:
            topic_scores[tname]["correct"] += 1

    for tname, stats in topic_scores.items():
        stats["percentage"] = int((stats["correct"] / stats["attempted"]) * 100)
        stats["is_weak"] = stats["percentage"] < 60

    context = {
        "session": session,
        "responses": responses,
        "grade": grade,
        "grade_color": grade_color,
        "topic_scores": topic_scores,
    }
    return render(request, "practice/session_results.html", context)
