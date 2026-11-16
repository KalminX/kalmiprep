from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.forms import RegistrationForm, StudentProfileForm
from accounts.models import StudentProfile
from practice.models import PracticeSession
from progress.models import Bookmark, TopicMastery


def _migrate_guest_data_to_user(session_key, user):
    """
    Transfers bookmarks, practice sessions, and topic mastery
    from guest session_key to the logged-in user account.
    """
    if not session_key:
        return

    # Migrate Practice Sessions
    PracticeSession.objects.filter(session_key=session_key, user__isnull=True).update(user=user)

    # Migrate Bookmarks (avoiding duplicate user bookmarks on same question)
    for bm in Bookmark.objects.filter(session_key=session_key, user__isnull=True):
        if not Bookmark.objects.filter(user=user, question=bm.question).exists():
            bm.user = user
            bm.save()
        else:
            bm.delete()

    # Migrate Topic Mastery records
    for tm in TopicMastery.objects.filter(session_key=session_key, user__isnull=True):
        user_tm, created = TopicMastery.objects.get_or_create(user=user, topic=tm.topic)
        if not created:
            user_tm.questions_attempted += tm.questions_attempted
            user_tm.questions_correct += tm.questions_correct
            user_tm.save()
            tm.delete()
        else:
            tm.user = user
            tm.save()


def register_view(request):
    if request.user.is_authenticated:
        return redirect("progress:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            guest_session_key = request.session.session_key
            user = form.save()
            login(request, user)
            _migrate_guest_data_to_user(guest_session_key, user)
            messages.success(request, f"Welcome to KalmiPrep, {user.first_name or user.username}!")
            return redirect("progress:dashboard")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    next_param = request.POST.get("next") or request.GET.get("next") or ""
    if request.user.is_authenticated:
        if next_param and url_has_allowed_host_and_scheme(next_param, allowed_hosts={request.get_host()}):
            return redirect(next_param)
        return redirect("progress:dashboard")

    error_msg = None
    if request.method == "POST":
        username_val = request.POST.get("username", "").strip()
        password_val = request.POST.get("password", "").strip()
        user = authenticate(request, username=username_val, password=password_val)

        if user is not None:
            guest_session_key = request.session.session_key
            login(request, user)
            _migrate_guest_data_to_user(guest_session_key, user)

            # Auto-ensure StudentProfile for non-staff students without profile
            if not user.is_staff and not user.is_superuser:
                StudentProfile.objects.get_or_create(user=user)

            target_url = next_param
            if not target_url or not url_has_allowed_host_and_scheme(target_url, allowed_hosts={request.get_host()}):
                target_url = reverse("progress:dashboard")

            # If HTMX boosted or swapped request, trigger full window redirect
            if request.headers.get("HX-Request"):
                response = HttpResponse(status=200)
                response["HX-Redirect"] = target_url
                return response

            return redirect(target_url)
        else:
            error_msg = "Invalid username or password. Please verify and try again."

    return render(request, "accounts/login.html", {"error": error_msg, "next": next_param})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    redirect_target = reverse("core:landing")

    if request.headers.get("HX-Request"):
        response = HttpResponse(status=200)
        response["HX-Redirect"] = redirect_target
        return response

    return redirect(redirect_target)


@login_required
def profile_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            # Update User fields
            request.user.first_name = form.cleaned_data.get("first_name", request.user.first_name)
            request.user.last_name = form.cleaned_data.get("last_name", request.user.last_name)
            request.user.email = form.cleaned_data.get("email", request.user.email)
            request.user.save()

            messages.success(request, "Profile preferences updated successfully.")
            return redirect("accounts:profile")
    else:
        initial_data = {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        }
        form = StudentProfileForm(instance=profile, initial=initial_data)

    return render(request, "accounts/profile.html", {"form": form, "profile": profile})
