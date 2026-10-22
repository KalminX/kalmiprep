from django.shortcuts import get_object_or_404, render
from curriculum.models import Subject, Topic, Subtopic
from questions.models import Question


def subject_list(request):
    """Lists all available subjects with question counts and curriculum coverage."""
    subjects = Subject.objects.filter(is_active=True).prefetch_related("topics", "questions")
    return render(request, "curriculum/subject_list.html", {"subjects": subjects})


def subject_detail(request, slug):
    """Displays subject overview, syllabus topics, and practice launchers."""
    subject = get_object_or_404(Subject, slug=slug, is_active=True)
    topics = subject.topics.all().prefetch_related("subtopics", "questions")
    
    # Calculate questions by exam type in this subject
    exam_breakdown = {
        "UTME": subject.questions.filter(exam_type="UTME", is_published=True).count(),
        "WAEC": subject.questions.filter(exam_type="WAEC", is_published=True).count(),
        "NECO": subject.questions.filter(exam_type="NECO", is_published=True).count(),
    }

    context = {
        "subject": subject,
        "topics": topics,
        "exam_breakdown": exam_breakdown,
        "total_subject_questions": subject.question_count,
    }
    return render(request, "curriculum/subject_detail.html", context)


def topic_detail(request, subject_slug, topic_slug):
    """Deep dive into a syllabus topic with subtopics, question breakdown, and practice launchers."""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, subject=subject, slug=topic_slug)
    subtopics = topic.subtopics.all()
    
    questions_count = topic.questions.filter(is_published=True).count()
    recent_questions = topic.questions.filter(is_published=True).prefetch_related("options")[:5]

    context = {
        "subject": subject,
        "topic": topic,
        "subtopics": subtopics,
        "questions_count": questions_count,
        "recent_questions": recent_questions,
    }
    return render(request, "curriculum/topic_detail.html", context)
