from django.shortcuts import render
from core.cache_utils import (
    get_cached_subject_list,
    get_cached_subject_detail,
    get_cached_topic_detail,
)


def subject_list(request):
    """Lists all available subjects with question counts and curriculum coverage."""
    subjects = get_cached_subject_list()
    return render(request, "curriculum/subject_list.html", {"subjects": subjects})


def subject_detail(request, slug):
    """Displays subject overview, syllabus topics, and practice launchers."""
    context = get_cached_subject_detail(slug)
    return render(request, "curriculum/subject_detail.html", context)


def topic_detail(request, subject_slug, topic_slug):
    """Deep dive into a syllabus topic with subtopics, question breakdown, and practice launchers."""
    context = get_cached_topic_detail(subject_slug, topic_slug)
    return render(request, "curriculum/topic_detail.html", context)
