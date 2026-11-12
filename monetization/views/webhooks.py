from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..services import PaymentError, accept_paystack_webhook

@require_POST
@csrf_exempt
def paystack_webhook(request):
    try:
        accept_paystack_webhook(request.body, request.headers.get("x-paystack-signature", ""))
    except PaymentError as exc:
        return HttpResponse(str(exc), status=400)
    except Exception:
        # Return non-2xx so Paystack retries; do not acknowledge an unprocessed event.
        return HttpResponse("Webhook processing failed.", status=503)
    return HttpResponse("ok", status=200)
