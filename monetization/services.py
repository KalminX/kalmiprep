import base64
import hashlib
import hmac
import json
import random
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.urls import reverse
from django.utils import timezone

from practice.models import PracticeQuestionResponse, PracticeSession
from questions.models import Question

from .models import (
    PaidTest,
    TeacherWallet,
    TestPurchase,
    TestRefund,
    WalletEntry,
    WebhookReceipt,
    WithdrawalRequest,
)

PAYSTACK_API = "https://api.paystack.co"
TEACHER_SHARE_PERCENT = Decimal("80")


class PaymentError(Exception):
    pass


def split_price(amount_kobo):
    teacher = int((Decimal(amount_kobo) * TEACHER_SHARE_PERCENT / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return teacher, amount_kobo - teacher


def _secret_key():
    return getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""


def _require_payment_key():
    if not getattr(settings, "PAID_TEST_PIN_SECRET", ""):
        raise PaymentError("Configure PAID_TEST_PIN_SECRET before enabling paid tests.")
    secret = _secret_key()
    test_mode = getattr(settings, "PAYSTACK_TEST_MODE", settings.DEBUG)
    required_prefix = "sk_test_" if test_mode else "sk_live_"
    if not secret or not secret.startswith(required_prefix):
        mode = "test" if test_mode else "live"
        raise PaymentError(f"Configure a Paystack {mode} secret key before enabling checkout.")
    return secret


def initialize_paystack_payment(purchase):
    secret = _require_payment_key()
    site_url = getattr(settings, "SITE_URL", "")
    if not site_url:
        raise PaymentError("Configure SITE_URL before enabling Paystack checkout.")
    callback_url = f"{site_url}{reverse('monetization:paystack_callback')}"
    payload = {
        "email": purchase.buyer_email,
        "amount": str(purchase.amount_kobo),
        "currency": "NGN",
        "reference": purchase.paystack_reference,
        "callback_url": callback_url,
        "metadata": {
            "purchase_id": str(purchase.pk),
            "test_id": purchase.test_id,
            "custom_fields": [{"display_name": "Test", "variable_name": "paid_test", "value": purchase.test.title}],
        },
    }
    try:
        response = requests.post(
            f"{PAYSTACK_API}/transaction/initialize",
            json=payload,
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaymentError("Could not start checkout. Please try again.") from exc
    if not body.get("status") or not body.get("data", {}).get("authorization_url"):
        raise PaymentError("The payment provider could not start checkout.")
    return body["data"]["authorization_url"]


def verify_paystack_transaction(reference):
    secret = _require_payment_key()
    try:
        response = requests.get(
            f"{PAYSTACK_API}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=15,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaymentError("Could not verify payment with the provider.") from exc
    if not body.get("status") or not isinstance(body.get("data"), dict):
        raise PaymentError("The provider did not confirm this payment.")
    return body["data"]


def _verified_purchase(reference, provider_data):
    purchase = TestPurchase.objects.select_for_update().filter(paystack_reference=reference).first()
    if not purchase:
        raise PaymentError("No matching checkout was found.")
    try:
        amount = int(provider_data.get("amount", -1))
    except (TypeError, ValueError):
        amount = -1
    if (
        provider_data.get("status") != "success"
        or provider_data.get("reference") != purchase.paystack_reference
        or amount != purchase.amount_kobo
        or provider_data.get("currency") != "NGN"
    ):
        raise PaymentError("Payment details did not match this test checkout.")
    return purchase, provider_data


@transaction.atomic
def record_verified_payment(reference, provider_data):
    purchase, provider_data = _verified_purchase(reference, provider_data)
    if purchase.status in (TestPurchase.Status.REFUNDED, TestPurchase.Status.PARTIALLY_REFUNDED):
        return purchase
    if purchase.status == TestPurchase.Status.PAID:
        return purchase
    wallet, _ = TeacherWallet.objects.get_or_create(teacher=purchase.teacher)
    entry, created = WalletEntry.objects.get_or_create(
        kind=WalletEntry.Kind.TEST_SALE,
        source_reference=f"paystack:{reference}",
        defaults={
            "wallet": wallet,
            "purchase": purchase,
            "amount_kobo": purchase.teacher_share_kobo,
        },
    )
    if created:
        TeacherWallet.objects.filter(pk=wallet.pk).update(balance_kobo=F("balance_kobo") + entry.amount_kobo)
    purchase.status = TestPurchase.Status.PAID
    purchase.paid_at = timezone.now()
    provider_id = provider_data.get("id")
    if provider_id is not None:
        purchase.paystack_transaction_id = str(provider_id)
    if provider_data.get("fees") is not None:
        purchase.gateway_fee_kobo = max(0, int(provider_data["fees"]))
    pin = access_pin_for(purchase)
    purchase.access_pin_hash = pin_hash(pin)
    purchase.save(update_fields=["status", "paid_at", "paystack_transaction_id", "gateway_fee_kobo", "access_pin_hash"])
    _send_purchase_pin_email(purchase, pin)
    return purchase


def _send_purchase_pin_email(purchase, pin):
    if not purchase.buyer_email:
        return
    from django.core.mail import send_mail

    site_url = getattr(settings, "SITE_URL", "https://kalmiprep.kalmitech.app").rstrip("/")
    start_url = f"{site_url}/monetization/t/{purchase.test.share_code}/enter/"
    subject = f"Your KalmiPrep Test Access PIN: {purchase.test.title}"
    body = (
        f"Hello {purchase.buyer_name or 'Learner'},\n\n"
        f"Thank you for purchasing access to '{purchase.test.title}' by {purchase.teacher.display_name}.\n\n"
        f"Your 10-character Test Access PIN is:\n\n"
        f"    {pin}\n\n"
        f"You can start or resume your test at any time using this link:\n"
        f"{start_url}\n\n"
        f"Payment Reference: {purchase.paystack_reference}\n"
        f"Amount: ₦{purchase.amount_kobo / 100:.2f}\n\n"
        f"Best regards,\n"
        f"The KalmiPrep Team"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "KalmiPrep <noreply@kalmiprep.com>"),
            recipient_list=[purchase.buyer_email],
            fail_silently=True,
        )
    except Exception:
        pass


def pin_hash(pin):
    return hashlib.sha256(pin.encode("ascii")).hexdigest()


def access_pin_for(purchase):
    pin_secret = getattr(settings, "PAID_TEST_PIN_SECRET", "")
    if not pin_secret:
        raise PaymentError("Configure PAID_TEST_PIN_SECRET before issuing test access PINs.")
    key = str(pin_secret).encode("utf-8")
    message = b"kalmiprep-paid-test:" + purchase.pk.bytes
    digest = hmac.new(key, message, hashlib.sha256).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=")[:10]


@transaction.atomic
def apply_processed_refund(purchase_reference, refund_reference, amount_kobo):
    purchase = TestPurchase.objects.select_for_update().filter(paystack_reference=purchase_reference).first()
    if not purchase or purchase.status not in (TestPurchase.Status.PAID, TestPurchase.Status.PARTIALLY_REFUNDED):
        raise PaymentError("Refund does not match a paid test checkout.")
    amount_kobo = int(amount_kobo)
    if amount_kobo <= 0 or purchase.refunded_kobo + amount_kobo > purchase.amount_kobo:
        raise PaymentError("Refund amount is invalid for this checkout.")
    refund, created = TestRefund.objects.get_or_create(
        provider_reference=refund_reference,
        defaults={"purchase": purchase, "amount_kobo": amount_kobo},
    )
    if not created:
        if refund.purchase_id != purchase.pk or refund.amount_kobo != amount_kobo:
            raise PaymentError("A refund reference was reused with different details.")
        return purchase

    old_refunded = purchase.refunded_kobo
    new_refunded = old_refunded + amount_kobo
    old_teacher_refund = int(
        (Decimal(old_refunded) * Decimal(purchase.teacher_share_kobo) / Decimal(purchase.amount_kobo)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    new_teacher_refund = int(
        (Decimal(new_refunded) * Decimal(purchase.teacher_share_kobo) / Decimal(purchase.amount_kobo)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    teacher_debit = new_teacher_refund - old_teacher_refund
    if teacher_debit:
        wallet = TeacherWallet.objects.select_for_update().get(teacher=purchase.teacher)
        WalletEntry.objects.create(
            wallet=wallet,
            purchase=purchase,
            kind=WalletEntry.Kind.REFUND,
            amount_kobo=-teacher_debit,
            source_reference=f"paystack-refund:{refund_reference}",
        )
        TeacherWallet.objects.filter(pk=wallet.pk).update(balance_kobo=F("balance_kobo") - teacher_debit)
    purchase.refunded_kobo = new_refunded
    purchase.status = (
        TestPurchase.Status.REFUNDED
        if new_refunded == purchase.amount_kobo
        else TestPurchase.Status.PARTIALLY_REFUNDED
    )
    purchase.save(update_fields=["refunded_kobo", "status"])
    return purchase


@transaction.atomic
def start_paid_test_attempt(purchase, session_key=""):
    purchase = TestPurchase.objects.select_for_update().get(pk=purchase.pk)
    if purchase.status != TestPurchase.Status.PAID:
        raise PaymentError("This test purchase is not available for an attempt.")
    if purchase.practice_session_id:
        return purchase.practice_session

    paid_test = purchase.test
    if paid_test.randomization == PaidTest.Randomization.SHARED_SET:
        candidates = list(Question.objects.filter(pk__in=paid_test.fixed_question_ids, is_published=True))
    else:
        candidates = list(
            Question.objects.filter(topic__in=paid_test.topics.all(), is_published=True)
            .distinct()
            .order_by("pk")
        )
        if len(candidates) < paid_test.question_count:
            raise PaymentError("The teacher's question pool is no longer large enough to start this test.")
        candidates = random.SystemRandom().sample(candidates, paid_test.question_count)
    if len(candidates) != paid_test.question_count:
        raise PaymentError("This test does not have enough available questions.")
    random.SystemRandom().shuffle(candidates)

    first_topic = paid_test.topics.select_related("subject").first()
    subject = first_topic.subject if first_topic else None

    session = PracticeSession.objects.create(
        user=purchase.buyer,
        session_key=session_key if not purchase.buyer_id else "",
        mode=PracticeSession.Mode.CBT_MOCK,
        title=paid_test.title,
        subject=subject,
        topic=None,
        exam_type=None,
        total_questions=len(candidates),
        time_limit_seconds=paid_test.time_limit_minutes * 60,
        status=PracticeSession.Status.IN_PROGRESS,
    )
    for index, question in enumerate(candidates, start=1):
        PracticeQuestionResponse.objects.create(session=session, question=question, order=index)
    purchase.practice_session = session
    purchase.save(update_fields=["practice_session"])
    return session


def accept_paystack_webhook(raw_body, signature):
    secret = _require_payment_key()
    if not signature:
        raise PaymentError("Webhook signature is missing.")
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise PaymentError("Webhook signature is invalid.")
    try:
        event = json.loads(raw_body)
    except (TypeError, ValueError) as exc:
        raise PaymentError("Webhook body is not valid JSON.") from exc
    if not isinstance(event, dict) or not isinstance(event.get("data"), dict):
        raise PaymentError("Webhook payload is malformed.")

    fingerprint = hashlib.sha256(raw_body).hexdigest()
    if WebhookReceipt.objects.filter(payload_fingerprint=fingerprint).exists():
        return
    event_name = str(event.get("event", ""))[:80]
    data = event["data"]
    verified = None
    reference = None
    if event_name == "charge.success":
        reference = data.get("reference")
        if not reference:
            raise PaymentError("Successful charge event has no reference.")
        # Do not hold a database transaction open while making the verification request.
        verified = verify_paystack_transaction(reference)
    with transaction.atomic():
        receipt, created = WebhookReceipt.objects.get_or_create(
            payload_fingerprint=fingerprint, defaults={"event_name": event_name}
        )
        if not created:
            return
        if event_name == "charge.success":
            record_verified_payment(reference, verified)
        elif event_name == "refund.processed":
            reference = data.get("transaction_reference") or data.get("reference")
            refund_reference = data.get("refund_reference") or data.get("id")
            amount = data.get("amount")
            if not reference or not amount:
                raise PaymentError("Processed refund event is missing its reference or amount.")
            if not refund_reference:
                refund_reference = hashlib.sha256(
                    json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
            apply_processed_refund(reference, str(refund_reference), int(amount))


@transaction.atomic
def mark_withdrawal_paid(withdrawal_id):
    withdrawal = WithdrawalRequest.objects.select_for_update().select_related("wallet").get(pk=withdrawal_id)
    if withdrawal.status == WithdrawalRequest.Status.PAID:
        return withdrawal
    if withdrawal.status not in (WithdrawalRequest.Status.REQUESTED, WithdrawalRequest.Status.APPROVED):
        raise PaymentError("Only requested or approved withdrawals can be marked paid.")
    wallet = TeacherWallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
    if wallet.balance_kobo < withdrawal.amount_kobo:
        raise PaymentError("Wallet balance no longer covers this withdrawal.")
    _, created = WalletEntry.objects.get_or_create(
        kind=WalletEntry.Kind.WITHDRAWAL,
        source_reference=f"withdrawal:{withdrawal.pk}",
        defaults={"wallet": wallet, "purchase": None, "amount_kobo": -withdrawal.amount_kobo},
    )
    if created:
        TeacherWallet.objects.filter(pk=wallet.pk).update(balance_kobo=F("balance_kobo") - withdrawal.amount_kobo)
    withdrawal.status = WithdrawalRequest.Status.PAID
    withdrawal.reviewed_at = timezone.now()
    withdrawal.save(update_fields=["status", "reviewed_at"])
    return withdrawal


@transaction.atomic
def request_withdrawal(wallet, amount_kobo):
    wallet = TeacherWallet.objects.select_for_update().get(pk=wallet.pk)
    amount_kobo = int(amount_kobo)
    reserved = WithdrawalRequest.objects.filter(
        wallet=wallet,
        status__in=[WithdrawalRequest.Status.REQUESTED, WithdrawalRequest.Status.APPROVED],
    ).aggregate(total=Sum("amount_kobo"))["total"] or 0
    if amount_kobo <= 0 or amount_kobo + reserved > wallet.balance_kobo:
        raise PaymentError("This request exceeds your available wallet balance.")
    return WithdrawalRequest.objects.create(wallet=wallet, amount_kobo=amount_kobo)

