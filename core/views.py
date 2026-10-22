from django.shortcuts import render
from core.cache_utils import get_cached_landing_metrics


def landing(request):
    """
    Landing Page for KalmiPrep by Kalmitech.
    Presents the deliberate learning philosophy, subject catalog, real question counts,
    interactive preview of the KaTeX question experience, and target exams.
    Backed by Redis caching with automatic invalidation.
    """
    context = get_cached_landing_metrics()
    return render(request, "core/landing.html", context)
