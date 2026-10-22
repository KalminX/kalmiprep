from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from questions.models import Question
from questions.filters import QuestionFilter
from progress.models import Bookmark


def question_list(request):
    """
    Searchable Question Library with multi-facet filters (Subject, Exam, Year, Topic, Diagrams, Solutions).
    Supports server-side pagination and HTMX partial swapping.
    """
    queryset = (
        Question.objects.filter(is_published=True)
        .select_related("subject", "topic")
        .prefetch_related("options")
    )

    # Sorting
    sort = request.GET.get("sort", "-exam_year")
    if sort in ["-exam_year", "exam_year", "-id", "id"]:
        queryset = queryset.order_by(sort, "id")

    # Apply Filters
    filterset = QuestionFilter(request.GET, queryset=queryset)
    filtered_qs = filterset.qs

    # Pagination: 15 questions per page
    paginator = Paginator(filtered_qs, 15)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Determine user's bookmarked question IDs
    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(Bookmark.objects.filter(user=request.user).values_list("question_id", flat=True))
    elif request.session.session_key:
        bookmarked_ids = set(Bookmark.objects.filter(session_key=request.session.session_key).values_list("question_id", flat=True))

    context = {
        "filter": filterset,
        "page_obj": page_obj,
        "total_results": filtered_qs.count(),
        "bookmarked_ids": bookmarked_ids,
        "sort": sort,
    }

    # If request is HTMX, return only the results container partial
    if request.headers.get("HX-Request"):
        return render(request, "questions/partials/question_results_list.html", context)

    return render(request, "questions/question_list.html", context)


def study_question(request, pk):
    """
    Study Mode for a single question.
    Displays full question, KaTeX formulas, diagrams, options, and toggleable step-by-step solution.
    Provides previous/next navigation within the subject/topic context.
    """
    question = get_object_or_404(
        Question.objects.select_related("subject", "topic").prefetch_related("options"),
        pk=pk,
        is_published=True,
    )

    # Contextual Prev / Next questions within same subject
    prev_question = (
        Question.objects.filter(subject=question.subject, is_published=True, id__lt=question.id)
        .order_by("-id")
        .first()
    )
    next_question = (
        Question.objects.filter(subject=question.subject, is_published=True, id__gt=question.id)
        .order_by("id")
        .first()
    )

    # Check bookmark status
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(user=request.user, question=question).exists()
    elif request.session.session_key:
        is_bookmarked = Bookmark.objects.filter(session_key=request.session.session_key, question=question).exists()

    context = {
        "question": question,
        "options": question.options.all(),
        "prev_question": prev_question,
        "next_question": next_question,
        "is_bookmarked": is_bookmarked,
    }
    return render(request, "questions/study_question.html", context)


@require_POST
def toggle_bookmark(request, pk):
    """
    HTMX Endpoint to toggle a bookmark on a question.
    Supports both authenticated user accounts and anonymous guest sessions.
    """
    question = get_object_or_404(Question, pk=pk)
    
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    is_bookmarked = False
    if request.user.is_authenticated:
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, question=question)
        if not created:
            bookmark.delete()
            is_bookmarked = False
        else:
            is_bookmarked = True
        total_bookmarks = Bookmark.objects.filter(user=request.user).count()
    else:
        bookmark, created = Bookmark.objects.get_or_create(session_key=session_key, question=question)
        if not created:
            bookmark.delete()
            is_bookmarked = False
        else:
            is_bookmarked = True
        total_bookmarks = Bookmark.objects.filter(session_key=session_key).count()

    response = render(
        request,
        "questions/partials/bookmark_button.html",
        {
            "question": question,
            "is_bookmarked": is_bookmarked,
        },
    )
    # Trigger client-side event to update navbar bookmark badge counter
    response["HX-Trigger"] = json_trigger = '{"bookmarkCountUpdated": ' + str(total_bookmarks) + '}'
    return response
