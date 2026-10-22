from django.shortcuts import render
from curriculum.models import Subject, Topic
from questions.models import Question
from practice.models import PracticeSession


def landing(request):
    """
    Landing Page for KalmiPrep by Kalmitech.
    Presents the deliberate learning philosophy, subject catalog, real question counts,
    interactive preview of the KaTeX question experience, and target exams.
    """
    subjects = Subject.objects.filter(is_active=True).prefetch_related("topics", "questions")
    
    # Real metrics (never fabricated)
    total_questions = Question.objects.filter(is_published=True).count()
    total_topics = Topic.objects.count()
    total_with_solutions = Question.objects.filter(is_published=True).exclude(explanation="").count()
    
    # Representative sample question for interactive preview
    preview_question = (
        Question.objects.filter(
            is_published=True,
            subject__slug="mathematics",
        )
        .exclude(explanation="")
        .prefetch_related("options")
        .first()
    )

    context = {
        "subjects": subjects,
        "total_questions": total_questions,
        "total_topics": total_topics,
        "total_with_solutions": total_with_solutions,
        "preview_question": preview_question,
    }
    return render(request, "core/landing.html", context)
