import json
from django.shortcuts import get_object_or_404, render
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from core.cache_utils import get_cached_filter_choices
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

    # Apply Filters (mapping 'exam' alias to 'exam_type' if needed)
    filter_data = request.GET.copy()
    if "exam" in filter_data and not filter_data.get("exam_type"):
        filter_data["exam_type"] = filter_data["exam"]

    filterset = QuestionFilter(filter_data, queryset=queryset)
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

    choices_data = get_cached_filter_choices()
    topics_by_subject = choices_data.get("topics_by_subject", {})

    search_query = request.GET.get("search", "")

    is_htmx_results = bool(
        request.headers.get("HX-Request") and request.headers.get("HX-Target") == "question-results-container"
    )

    context = {
        "filter": filterset,
        "page_obj": page_obj,
        "total_results": paginator.count,
        "bookmarked_ids": bookmarked_ids,
        "sort": sort,
        "topics_by_subject_json": json.dumps(topics_by_subject),
        "search_query": search_query,
        "is_htmx_results": is_htmx_results,
    }

    # If request is an HTMX query targeting the internal results container, return only the results partial
    if is_htmx_results:
        return render(request, "questions/partials/question_results_list.html", context)

    return render(request, "questions/question_list.html", context)


def study_question(request, pk):
    """
    Study Mode for a single question.
    Displays full question, KaTeX formulas, diagrams, options, and toggleable step-by-step solution.
    Provides previous/next navigation within the subject/topic context.
    Question details are cached in Redis with instant response.
    """
    cache_key = f"kalmiprep:q:study:{pk}"
    cached_payload = cache.get(cache_key)

    if cached_payload is None:
        question = get_object_or_404(
            Question.objects.select_related("subject", "topic").prefetch_related("options"),
            pk=pk,
            is_published=True,
        )
        options = list(question.options.all())
        prev_question_id = (
            Question.objects.filter(subject=question.subject, is_published=True, id__lt=question.id)
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
        )
        next_question_id = (
            Question.objects.filter(subject=question.subject, is_published=True, id__gt=question.id)
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )
        cached_payload = {
            "question": question,
            "options": options,
            "prev_question_id": prev_question_id,
            "next_question_id": next_question_id,
        }
        cache.set(cache_key, cached_payload, 3600)

    question = cached_payload["question"]
    options = cached_payload["options"]
    prev_question_id = cached_payload["prev_question_id"]
    next_question_id = cached_payload["next_question_id"]

    # Check bookmark status (user-isolated, evaluated dynamically)
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(user=request.user, question_id=pk).exists()
    elif request.session.session_key:
        is_bookmarked = Bookmark.objects.filter(session_key=request.session.session_key, question_id=pk).exists()

    search_query = request.GET.get("search", "")

    context = {
        "question": question,
        "options": options,
        "prev_question": {"id": prev_question_id} if prev_question_id else None,
        "next_question": {"id": next_question_id} if next_question_id else None,
        "is_bookmarked": is_bookmarked,
        "search_query": search_query,
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
