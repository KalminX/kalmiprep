import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import StudentProfile

from .models import TeacherInvitation, TeacherProfile


INVITATION_TTL = timedelta(days=7)


def issue_teacher_invitation(*, email, kind, display_name, created_by, request):
    email = email.strip().lower()
    user_model = get_user_model()
    if user_model.objects.filter(email__iexact=email).count() > 1:
        raise ValueError("This email belongs to more than one account. Resolve the duplicate accounts first.")

    now = timezone.now()
    TeacherInvitation.objects.filter(
        email__iexact=email, accepted_at__isnull=True, revoked_at__isnull=True
    ).update(revoked_at=now)

    raw_token = secrets.token_urlsafe(32)
    invitation = TeacherInvitation.objects.create(
        email=email,
        kind=kind,
        display_name=display_name.strip(),
        token_hash=hashlib.sha256(raw_token.encode("ascii")).hexdigest(),
        created_by=created_by,
        expires_at=now + INVITATION_TTL,
    )
    invitation_url = request.build_absolute_uri(
        reverse("monetization:accept_teacher_invitation", args=[invitation.pk, raw_token])
    )
    try:
        sent = send_mail(
            "Your KalmiPrep teacher account",
            (
                f"You have been invited to teach on KalmiPrep as {display_name}.\n\n"
                f"Set up your account using this one-time link (valid for 7 days):\n{invitation_url}\n\n"
                "If you already have a KalmiPrep account, sign in with that account before accepting."
            ),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        if sent != 1:
            raise RuntimeError("The invitation email was not accepted by the email backend.")
    except Exception:
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])
        raise
    return invitation


def invitation_matches(invitation, raw_token):
    if not invitation or not raw_token or not invitation.is_usable:
        return False
    try:
        token_bytes = raw_token.encode("ascii")
    except UnicodeEncodeError:
        return False
    return secrets.compare_digest(
        invitation.token_hash,
        hashlib.sha256(token_bytes).hexdigest(),
    )


@transaction.atomic
def accept_teacher_invitation(*, invitation_id, raw_token, user=None, account_data=None):
    invitation = TeacherInvitation.objects.select_for_update().filter(pk=invitation_id).first()
    if not invitation_matches(invitation, raw_token):
        raise ValueError("This invitation is invalid, expired, or already used.")

    user_model = get_user_model()
    existing = list(user_model.objects.filter(email__iexact=invitation.email)[:2])
    if len(existing) > 1:
        raise ValueError("This email matches multiple accounts. Contact support to resolve it.")
    if existing:
        if not user or user.pk != existing[0].pk:
            raise ValueError("Sign in to the KalmiPrep account that uses this email, then accept the invitation.")
        account = existing[0]
    else:
        if user:
            raise ValueError("Sign out before creating the account for this invitation.")
        if not account_data:
            raise ValueError("Account details are required to accept this invitation.")
        account = user_model.objects.create_user(
            username=account_data["username"],
            email=invitation.email,
            first_name=account_data["first_name"],
            last_name=account_data.get("last_name", ""),
            password=account_data["password"],
        )
        StudentProfile.objects.get_or_create(user=account)

    profile, _ = TeacherProfile.objects.get_or_create(
        user=account,
        defaults={
            "kind": invitation.kind,
            "display_name": invitation.display_name,
            "status": TeacherProfile.Status.ACTIVE,
        },
    )
    profile.kind = invitation.kind
    profile.display_name = invitation.display_name
    profile.status = TeacherProfile.Status.ACTIVE
    profile.save(update_fields=["kind", "display_name", "status"])
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    return account
