import json
import logging
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.cache_utils import get_cached_landing_metrics
from core.models import SystemErrorLog

logger = logging.getLogger("core.telemetry")


def landing(request):
    """
    Landing Page for KalmiPrep by Kalmitech.
    Presents the deliberate learning philosophy, subject catalog, real question counts,
    interactive preview of the KaTeX question experience, and target exams.
    Backed by Redis caching with automatic invalidation.
    """
    context = get_cached_landing_metrics()
    return render(request, "core/landing.html", context)


def docs_view(request):
    """
    Interactive Testing and Architecture Guide for KalmiPrep.
    Details teacher test creation, proctor waiting lobby, demo DB payments,
    and admin earnings tracking.
    """
    return render(request, "docs/index.html")


@csrf_exempt
@require_POST
def telemetry_beacon_view(request):
    """
    Asynchronous Client-Side Error & Diagnostic Beacon.
    Receives uncaught JS exceptions, KaTeX math parsing failures, and network drop events
    from candidate browsers via navigator.sendBeacon() without interrupting the user.
    """
    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(body)
    except Exception as exc:
        logger.warning(f"Malformed telemetry beacon received: {exc}")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    message = str(data.get("message", "Unknown Client Error"))[:500]
    stack_trace = str(data.get("stack_trace", ""))
    path = str(data.get("path", request.META.get("HTTP_REFERER", "")))[:255]
    domain_val = data.get("domain", SystemErrorLog.Domain.CLIENT_JS)
    if domain_val not in SystemErrorLog.Domain.values:
        domain_val = SystemErrorLog.Domain.CLIENT_JS

    severity_val = data.get("severity", SystemErrorLog.Severity.ERROR)
    if severity_val not in SystemErrorLog.Severity.values:
        severity_val = SystemErrorLog.Severity.ERROR

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {"raw": str(metadata)}

    # Attach request context
    metadata["user_agent"] = request.META.get("HTTP_USER_AGENT", "")
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    try:
        log_entry = SystemErrorLog.objects.create(
            severity=severity_val,
            domain=domain_val,
            message=message,
            stack_trace=stack_trace,
            path=path,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip if ip else None,
            metadata=metadata,
        )
        logger.info(f"Persisted client error log: {log_entry.id} [{domain_val}] {message}")
    except Exception as exc:
        logger.error(f"Failed to persist client error log: {exc}")
        return JsonResponse({"status": "error", "message": "Failed to log"}, status=500)

    return HttpResponse(status=204)
