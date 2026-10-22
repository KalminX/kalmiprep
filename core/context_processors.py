from datetime import datetime
from curriculum.models import Subject
from progress.models import Bookmark

def kalmiprep_global_context(request):
    try:
        subjects = Subject.objects.filter(is_active=True).order_by("order", "name")
    except Exception:
        subjects = []

    # Count bookmarks
    bookmark_count = 0
    try:
        if request.user.is_authenticated:
            bookmark_count = Bookmark.objects.filter(user=request.user).count()
        elif request.session.session_key:
            bookmark_count = Bookmark.objects.filter(session_key=request.session.session_key).count()
    except Exception:
        bookmark_count = 0

    return {
        "global_subjects": subjects,
        "PLATFORM_NAME": "KalmiPrep",
        "PARENT_COMPANY": "Kalmitech",
        "TAGLINE": "Understand every topic. Prepare for every question.",
        "CURRENT_YEAR": datetime.now().year,
        "EXAM_CHOICES": [
            ("UTME", "UTME / JAMB"),
            ("WAEC", "WAEC / WASSCE"),
            ("NECO", "NECO SSCE"),
        ],
        "global_bookmark_count": bookmark_count,
    }
