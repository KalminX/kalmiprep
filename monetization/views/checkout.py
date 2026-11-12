import hashlib
import secrets

from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..forms import PinForm, TestCheckoutForm
from ..models import PaidTest, TeacherProfile, TestPurchase
from ..services import (
    PaymentError,
    access_pin_for,
    initialize_paystack_payment,
    pin_hash,
    record_verified_payment,
    split_price,
    start_paid_test_attempt,
    verify_paystack_transaction,
)

def public_test(request, share_code):
    paid_test = get_object_or_404(
        PaidTest.objects.select_related("teacher"), share_code=share_code, is_published=True,
        teacher__status=TeacherProfile.Status.ACTIVE,
    )
    if request.method == "POST":
        form = TestCheckoutForm(request.POST)
        if form.is_valid():
            teacher_share, platform_share = split_price(paid_test.price_kobo)
            reference = f"KALMI-{secrets.token_hex(14)}"
            purchase = TestPurchase.objects.create(
                test=paid_test,
                teacher=paid_test.teacher,
                buyer=request.user if request.user.is_authenticated else None,
                buyer_name=form.cleaned_data["name"],
                buyer_email=form.cleaned_data["email"],
                buyer_phone=form.cleaned_data["phone"],
                amount_kobo=paid_test.price_kobo,
                teacher_share_kobo=teacher_share,
                platform_share_kobo=platform_share,
                paystack_reference=reference,
            )
            # Demo Database Payment Bypass (No external Paystack required for testing)
            is_demo = (
                request.POST.get("payment_mode") == "demo"
                or not getattr(settings, "PAYSTACK_SECRET_KEY", "").strip()
                or getattr(settings, "PAYSTACK_TEST_MODE", True) and "demo" in request.POST
            )
            if is_demo:
                provider_data = {
                    "status": "success",
                    "reference": reference,
                    "amount": paid_test.price_kobo,
                    "currency": "NGN",
                    "id": f"demo-{secrets.token_hex(6)}",
                }
                record_verified_payment(reference, provider_data)
                return redirect(f"{reverse('monetization:paystack_callback')}?reference={reference}")

            try:
                checkout_url = initialize_paystack_payment(purchase)
            except PaymentError as exc:
                purchase.status = TestPurchase.Status.FAILED
                purchase.save(update_fields=["status"])
                form.add_error(None, str(exc))
            else:
                return redirect(checkout_url)
    else:
        form = TestCheckoutForm(initial={
            "name": request.user.get_full_name() if request.user.is_authenticated else "",
            "email": request.user.email if request.user.is_authenticated else "",
        })
    return render(request, "monetization/public_test.html", {"test": paid_test, "form": form})

def paystack_callback(request):
    reference = request.GET.get("reference", "").strip()
    if not reference:
        return HttpResponseBadRequest("Missing payment reference.")
    purchase = get_object_or_404(TestPurchase.objects.select_related("test", "test__teacher"), paystack_reference=reference)
    try:
        provider_data = verify_paystack_transaction(reference)
        purchase = record_verified_payment(reference, provider_data)
    except PaymentError as exc:
        return render(request, "monetization/payment_status.html", {"purchase": purchase, "error": str(exc)}, status=400)
    if purchase.status != TestPurchase.Status.PAID:
        return render(request, "monetization/payment_status.html", {"purchase": purchase, "error": "Payment is not complete."}, status=400)
    return render(request, "monetization/payment_success.html", {
        "purchase": purchase,
        "pin": access_pin_for(purchase),
    })

def enter_test(request, share_code):
    paid_test = get_object_or_404(PaidTest, share_code=share_code, is_published=True)
    if request.method == "POST":
        form = PinForm(request.POST)
        if form.is_valid():
            ip = request.META.get("REMOTE_ADDR", "unknown")
            throttle_key = "paid-test-pin-attempts:" + hashlib.sha256(f"{ip}:{share_code}".encode()).hexdigest()
            attempts = cache.get(throttle_key, 0)
            if attempts >= 12:
                form.add_error("pin", "Too many PIN attempts. Please try again in 15 minutes.")
                return render(request, "monetization/enter_test.html", {"test": paid_test, "form": form}, status=429)
            purchase = TestPurchase.objects.filter(
                test=paid_test,
                access_pin_hash=pin_hash(form.cleaned_data["pin"]),
                status=TestPurchase.Status.PAID,
            ).first()
            if not purchase:
                cache.add(throttle_key, 0, timeout=900)
                try:
                    attempts = cache.incr(throttle_key)
                except ValueError:
                    cache.set(throttle_key, 1, timeout=900)
                form.add_error("pin", "That access PIN is invalid or no longer active.")
            else:
                try:
                    cache.delete(throttle_key)
                    if not request.session.session_key:
                        request.session.create()
                    grants = set(request.session.get("paid_test_purchases", []))
                    grants.add(str(purchase.pk))
                    request.session["paid_test_purchases"] = list(grants)

                    if paid_test.requires_approval and not paid_test.is_approved_for_start:
                        return redirect("monetization:waiting_room", share_code=paid_test.share_code)

                    session = start_paid_test_attempt(purchase, request.session.session_key)
                except PaymentError as exc:
                    form.add_error(None, str(exc))
                else:
                    return redirect("practice:session_view", session_id=session.pk)
    else:
        form = PinForm()
    return render(request, "monetization/enter_test.html", {"test": paid_test, "form": form})

@login_required
def purchase_receipt(request, purchase_id):
    purchase = get_object_or_404(TestPurchase.objects.select_related("test"), pk=purchase_id)
    if purchase.buyer_id and purchase.buyer_id != request.user.id:
        raise PermissionDenied
    if purchase.status != TestPurchase.Status.PAID:
        raise PermissionDenied
    return render(request, "monetization/payment_success.html", {
        "purchase": purchase,
        "pin": access_pin_for(purchase),
    })

@login_required
@require_POST
def access_paid_purchase(request, purchase_id):
    purchase = get_object_or_404(TestPurchase, pk=purchase_id, buyer=request.user, status=TestPurchase.Status.PAID)
    if purchase.test.requires_approval and not purchase.test.is_approved_for_start:
        grants = set(request.session.get("paid_test_purchases", []))
        grants.add(str(purchase.pk))
        request.session["paid_test_purchases"] = list(grants)
        return redirect("monetization:waiting_room", share_code=purchase.test.share_code)
    try:
        session = start_paid_test_attempt(purchase, request.session.session_key or "")
    except PaymentError as exc:
        messages.error(request, str(exc))
        return redirect("monetization:purchase_receipt", purchase_id=purchase.pk)
    grants = set(request.session.get("paid_test_purchases", []))
    grants.add(str(purchase.pk))
    request.session["paid_test_purchases"] = list(grants)
    return redirect("practice:session_view", session_id=session.pk)


def waiting_room(request, share_code):
    paid_test = get_object_or_404(PaidTest.objects.select_related("teacher"), share_code=share_code, is_published=True)
    grants = request.session.get("paid_test_purchases", [])
    purchase = TestPurchase.objects.filter(pk__in=grants, test=paid_test, status=TestPurchase.Status.PAID).first()
    if not purchase:
        return redirect("monetization:enter_test", share_code=share_code)

    if paid_test.can_student_start:
        session = start_paid_test_attempt(purchase, request.session.session_key or "")
        return redirect("practice:session_view", session_id=session.pk)

    return render(request, "monetization/waiting_room.html", {
        "test": paid_test,
        "purchase": purchase,
        "pin": access_pin_for(purchase),
    })


def check_test_started(request, share_code):
    paid_test = get_object_or_404(PaidTest, share_code=share_code, is_published=True)
    if paid_test.can_student_start:
        grants = request.session.get("paid_test_purchases", [])
        purchase = TestPurchase.objects.filter(pk__in=grants, test=paid_test, status=TestPurchase.Status.PAID).first()
        if purchase:
            if not request.session.session_key:
                request.session.create()
            session = start_paid_test_attempt(purchase, request.session.session_key)
            target = reverse("practice:session_view", args=[session.pk])
            response = HttpResponse("Exam started! Launching...")
            response["HX-Redirect"] = target
            return response
        response = HttpResponse("Redirecting to start...")
        response["HX-Redirect"] = reverse("monetization:enter_test", args=[share_code])
        return response

    return HttpResponse(
        '<div class="flex items-center justify-center gap-2 text-xs font-semibold text-amber-600 dark:text-amber-400">'
        '<span class="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping"></span>'
        '<span>Waiting for teacher to unlock the exam...</span></div>'
    )
