import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import InvitationAccountForm, TeacherInvitationForm
from ..invitations import accept_teacher_invitation, invitation_matches, issue_teacher_invitation
from ..models import TeacherInvitation

logger = logging.getLogger(__name__)


@staff_member_required
def invite_teacher(request):
    if request.method == "POST":
        form = TeacherInvitationForm(request.POST)
        if form.is_valid():
            try:
                invitation = issue_teacher_invitation(
                    **form.cleaned_data,
                    created_by=request.user,
                    request=request,
                )
            except ValueError as exc:
                form.add_error(None, str(exc))
            except Exception:
                logger.exception("Unable to send teacher invitation email")
                form.add_error(None, "Could not send the invitation email. Check the configured email service and try again.")
            else:
                messages.success(request, f"Invitation sent to {invitation.email}.")
                return redirect("monetization:invite_teacher")
    else:
        form = TeacherInvitationForm()
    invitations = TeacherInvitation.objects.select_related("created_by")[:20]
    return render(request, "monetization/invite_teacher.html", {"form": form, "invitations": invitations})


def accept_invitation(request, invitation_id, token):
    invitation = get_object_or_404(TeacherInvitation, pk=invitation_id)
    if not invitation_matches(invitation, token):
        return render(request, "monetization/invitation_invalid.html", status=410)

    users = get_user_model().objects.filter(email__iexact=invitation.email)
    existing_count = users.count()
    if existing_count > 1:
        return render(request, "monetization/invitation_invalid.html", {
            "message": "This email matches multiple accounts. Contact KalmiPrep support to resolve it."
        }, status=409)
    existing_user = users.first()

    if existing_user and not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?next={request.path}"
        return render(request, "monetization/invitation_accept.html", {
            "invitation": invitation,
            "existing_account": True,
            "login_url": login_url,
        })
    if existing_user and request.user.pk != existing_user.pk:
        return render(request, "monetization/invitation_accept.html", {
            "invitation": invitation,
            "wrong_account": True,
            "login_url": reverse("accounts:logout"),
        })

    form = InvitationAccountForm(request.POST or None)
    if request.method == "POST":
        if existing_user:
            valid = True
        else:
            valid = form.is_valid()
            if valid:
                try:
                    pending_user = get_user_model()(
                        username=form.cleaned_data["username"],
                        email=invitation.email,
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                    )
                    validate_password(form.cleaned_data["password"], user=pending_user)
                except ValidationError as exc:
                    form.add_error("password", exc)
                    valid = False
        if valid:
            try:
                account = accept_teacher_invitation(
                    invitation_id=invitation.pk,
                    raw_token=token,
                    user=request.user if request.user.is_authenticated else None,
                    account_data=form.cleaned_data if not existing_user else None,
                )
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                if not request.user.is_authenticated:
                    login(request, account)
                messages.success(request, "Your teacher account is ready. Welcome to KalmiPrep.")
                return redirect("monetization:teacher_onboarding")

    return render(request, "monetization/invitation_accept.html", {
        "invitation": invitation,
        "form": form,
        "existing_account": bool(existing_user),
    })

