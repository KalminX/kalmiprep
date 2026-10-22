import logging
from django.core.cache import cache
from django.db.models import Count, Q

logger = logging.getLogger(__name__)

# Cache key constants
CACHE_KEY_GLOBAL_SUBJECTS = "kalmiprep:global_subjects"
CACHE_KEY_LANDING_METRICS = "kalmiprep:landing_metrics"
CACHE_KEY_SUBJECT_LIST = "kalmiprep:curriculum:subject_list"
CACHE_KEY_SUBJECT_DETAIL = "kalmiprep:curriculum:subject:{slug}"
CACHE_KEY_TOPIC_DETAIL = "kalmiprep:curriculum:topic:{subject_slug}:{topic_slug}"
CACHE_KEY_PRACTICE_SETUP = "kalmiprep:practice:setup_data"
CACHE_KEY_FILTER_CHOICES = "kalmiprep:questions:filter_choices"

# Default TTLs (in seconds)
TTL_SHORT = 300       # 5 minutes
TTL_MEDIUM = 1800     # 30 minutes
TTL_LONG = 3600 * 2   # 2 hours
TTL_DAY = 86400       # 24 hours


def get_cached_global_subjects():
    """
    Returns active subjects for the global navbar and dropdowns.
    Cached in Redis to avoid hitting Postgres on every single HTTP request.
    """
    subjects = cache.get(CACHE_KEY_GLOBAL_SUBJECTS)
    if subjects is None:
        from curriculum.models import Subject
        subjects = list(Subject.objects.filter(is_active=True).order_by("order", "name"))
        cache.set(CACHE_KEY_GLOBAL_SUBJECTS, subjects, TTL_LONG)
    return subjects


def get_cached_landing_metrics():
    """
    Computes verified question counts, topics count, and solution metrics for the landing page.
    Cached in Redis for 30 minutes.
    """
    data = cache.get(CACHE_KEY_LANDING_METRICS)
    if data is None:
        from curriculum.models import Subject, Topic
        from questions.models import Question

        subjects = list(
            Subject.objects.filter(is_active=True)
            .prefetch_related("topics")
            .annotate(
                total_pub_questions=Count("questions", filter=Q(questions__is_published=True)),
                total_pub_solutions=Count(
                    "questions",
                    filter=Q(questions__is_published=True) & ~Q(questions__explanation="")
                )
            )
        )
        total_questions = Question.objects.filter(is_published=True).count()
        total_topics = Topic.objects.count()
        total_with_solutions = Question.objects.filter(is_published=True).exclude(explanation="").count()

        preview_question = (
            Question.objects.filter(is_published=True, subject__slug="mathematics")
            .exclude(explanation="")
            .prefetch_related("options")
            .first()
        )

        data = {
            "subjects": subjects,
            "total_questions": total_questions,
            "total_topics": total_topics,
            "total_with_solutions": total_with_solutions,
            "preview_question": preview_question,
        }
        cache.set(CACHE_KEY_LANDING_METRICS, data, TTL_MEDIUM)
    return data


def get_cached_subject_list():
    """
    Returns subjects annotated with topic_count and question_count for the curriculum subject catalog.
    Cached in Redis.
    """
    subjects = cache.get(CACHE_KEY_SUBJECT_LIST)
    if subjects is None:
        from curriculum.models import Subject
        subjects = list(
            Subject.objects.filter(is_active=True)
            .annotate(
                num_topics=Count("topics", distinct=True),
                pub_question_count=Count("questions", filter=Q(questions__is_published=True), distinct=True)
            )
            .order_by("order", "name")
        )
        cache.set(CACHE_KEY_SUBJECT_LIST, subjects, TTL_LONG)
    return subjects


def get_cached_subject_detail(slug):
    """
    Caches subject overview, topics list, and exam breakdown for /curriculum/<slug>/.
    """
    key = CACHE_KEY_SUBJECT_DETAIL.format(slug=slug)
    data = cache.get(key)
    if data is None:
        from django.shortcuts import get_object_or_404
        from curriculum.models import Subject

        subject = get_object_or_404(Subject, slug=slug, is_active=True)
        topics = list(subject.topics.all().prefetch_related("subtopics", "questions"))

        exam_breakdown = {
            "UTME": subject.questions.filter(exam_type="UTME", is_published=True).count(),
            "WAEC": subject.questions.filter(exam_type="WAEC", is_published=True).count(),
            "NECO": subject.questions.filter(exam_type="NECO", is_published=True).count(),
        }

        data = {
            "subject": subject,
            "topics": topics,
            "exam_breakdown": exam_breakdown,
            "total_subject_questions": subject.question_count,
        }
        cache.set(key, data, TTL_LONG)
    return data


def get_cached_topic_detail(subject_slug, topic_slug):
    """
    Caches topic overview, subtopics, and questions count for /curriculum/<subject_slug>/<topic_slug>/.
    """
    key = CACHE_KEY_TOPIC_DETAIL.format(subject_slug=subject_slug, topic_slug=topic_slug)
    data = cache.get(key)
    if data is None:
        from django.shortcuts import get_object_or_404
        from curriculum.models import Subject, Topic

        subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
        topic = get_object_or_404(Topic, subject=subject, slug=topic_slug)
        subtopics = list(topic.subtopics.all())
        questions_count = topic.questions.filter(is_published=True).count()
        recent_questions = list(topic.questions.filter(is_published=True).prefetch_related("options")[:5])

        data = {
            "subject": subject,
            "topic": topic,
            "subtopics": subtopics,
            "questions_count": questions_count,
            "recent_questions": recent_questions,
        }
        cache.set(key, data, TTL_LONG)
    return data


def get_cached_practice_setup_data():
    """
    Prepares active subjects and topics for practice session setup dropdowns.
    """
    data = cache.get(CACHE_KEY_PRACTICE_SETUP)
    if data is None:
        from curriculum.models import Subject
        subjects = list(Subject.objects.filter(is_active=True).prefetch_related("topics"))
        data = {
            "subjects": subjects,
        }
        cache.set(CACHE_KEY_PRACTICE_SETUP, data, TTL_LONG)
    return data


def get_cached_filter_choices():
    """
    Caches the list of active subjects and topics for QuestionFilter dropdowns.
    Avoids expensive full-table queries during search and pagination.
    Returns (id, slug, name) tuples for subjects,
    and (id, slug, name, subject_id, subject_slug) tuples for topics.
    Also builds a pre-grouped topics_by_subject dictionary.
    """
    data = cache.get(CACHE_KEY_FILTER_CHOICES)
    if data is None:
        from curriculum.models import Subject, Topic
        subjects = list(Subject.objects.filter(is_active=True).order_by("order", "name").values_list("id", "slug", "name"))
        raw_topics = list(Topic.objects.all().order_by("subject__name", "name").values_list("id", "slug", "name", "subject_id", "subject__slug"))

        topics_by_subject = {}
        for tid, tslug, tname, sid, sslug in raw_topics:
            entry = {"id": tid, "slug": tslug, "name": tname}
            topics_by_subject.setdefault(sslug, []).append(entry)
            topics_by_subject.setdefault(str(sid), []).append(entry)

        data = {
            "subjects": subjects,
            "topics": raw_topics,
            "topics_by_subject": topics_by_subject,
        }
        cache.set(CACHE_KEY_FILTER_CHOICES, data, TTL_LONG)
    return data


def invalidate_all_curriculum_cache():
    """
    Invalidates curriculum, landing metrics, and setup data when subjects/topics/questions change.
    """
    keys_to_delete = [
        CACHE_KEY_GLOBAL_SUBJECTS,
        CACHE_KEY_LANDING_METRICS,
        CACHE_KEY_SUBJECT_LIST,
        CACHE_KEY_PRACTICE_SETUP,
        CACHE_KEY_FILTER_CHOICES,
    ]
    try:
        cache.delete_many(keys_to_delete)
        logger.info("Invalidated global curriculum and landing cache keys.")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache keys: {e}")
