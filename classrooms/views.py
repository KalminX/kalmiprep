import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from curriculum.models import Topic
from monetization.models import TeacherProfile

from .forms import ClassAssignmentForm, JoinClassForm, TeachingClassForm
from .models import ClassAssignment, ClassMembership, TeachingClass
from .results import teacher_assignment_rows
from .realtime import broadcast_class_update
from .services import create_teaching_class, join_class, start_assignment_attempt


def _active_teacher(user):
    teacher = getattr(user, "teacher_profile", None)
    return teacher if teacher and teacher.status == TeacherProfile.Status.ACTIVE else None


@login_required
def classroom_index(request):
    teacher = _active_teacher(request.user)
    classes = TeachingClass.objects.none()
    memberships = ClassMembership.objects.none()
    if teacher:
        classes = teacher.classrooms.prefetch_related("memberships", "assignments")
    memberships = request.user.class_memberships.select_related("classroom", "classroom__teacher")
    join_form = JoinClassForm()
    if request.method == "POST" and request.POST.get("action") == "join":
        join_form = JoinClassForm(request.POST)
        if join_form.is_valid():
            try:
                membership, created = join_class(
                    student=request.user,
                    join_code=join_form.cleaned_data["join_code"],
                )
            except ValueError as exc:
                join_form.add_error("join_code", str(exc))
            else:
                if created:
                    broadcast_class_update(membership.classroom_id)
                messages.success(request, "You joined the class." if created else "You are already in that class.")
                return redirect("classrooms:detail", class_id=membership.classroom_id)
    return render(request, "classrooms/index.html", {
        "teacher": teacher,
        "classes": classes,
        "memberships": memberships,
        "join_form": join_form,
        "class_form": TeachingClassForm(),
    })


@login_required
@require_POST
def create_class(request):
    teacher = _active_teacher(request.user)
    if not teacher:
        messages.warning(request, "An approved teacher account is required to create a class. Sign in as demo_teacher to manage classes.")
        return redirect("classrooms:index")
    form = TeachingClassForm(request.POST)
    if form.is_valid():
        classroom = create_teaching_class(teacher=teacher, name=form.cleaned_data["name"])
        messages.success(request, "Class created. Share its join code with your students.")
        return redirect("classrooms:detail", class_id=classroom.pk)
    messages.error(request, "Enter a name for your class.")
    return redirect("classrooms:index")


@login_required
def classroom_detail(request, class_id):
    classroom = get_object_or_404(
        TeachingClass.objects.select_related("teacher__user").prefetch_related("assignments"), pk=class_id
    )
    is_teacher = classroom.teacher.user_id == request.user.id
    if is_teacher and classroom.teacher.status != TeacherProfile.Status.ACTIVE:
        raise PermissionDenied("An active teacher account is required to manage this class.")
    membership = ClassMembership.objects.filter(classroom=classroom, student=request.user).first()
    if not is_teacher and not membership:
        raise PermissionDenied("Join this class to see its activities.")
    members = []
    topics_json = "[]"
    if is_teacher:
        members = classroom.memberships.select_related("student").order_by("joined_at")
        topics_data = list(
            Topic.objects.filter(subject__is_active=True).values("id", "name", "subject_id").order_by("order", "name")
        )
        topics_json = json.dumps(topics_data)
    return render(request, "classrooms/detail.html", {
        "classroom": classroom,
        "is_teacher": is_teacher,
        "membership": membership,
        "members": members,
        "assignment_form": ClassAssignmentForm(teacher=classroom.teacher),
        "topics_json": topics_json,
    })


@login_required
@require_POST
def create_assignment(request):
    teacher = _active_teacher(request.user)
    if not teacher:
        raise PermissionDenied("An approved teacher account is required to assign classwork.")
    form = ClassAssignmentForm(request.POST, teacher=teacher)
    if form.is_valid():
        assignment = form.save(commit=False)
        if assignment.classroom.teacher_id != teacher.pk:
            raise PermissionDenied
        assignment.save()
        form.save_m2m()
        messages.success(request, "Assignment published to your class.")
        return redirect("classrooms:assignment_detail", assignment_id=assignment.pk)
    # Keep form errors visible instead of silently losing a potentially detailed question-pool error.
    classrooms = teacher.classrooms.all()
    return render(request, "classrooms/assignment_form.html", {"form": form, "classrooms": classrooms}, status=400)


@login_required
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(
        ClassAssignment.objects.select_related("classroom__teacher__user", "subject", "topic").prefetch_related("elective_subjects"),
        pk=assignment_id,
    )
    is_teacher = assignment.classroom.teacher.user_id == request.user.id
    if is_teacher and assignment.classroom.teacher.status != TeacherProfile.Status.ACTIVE:
        raise PermissionDenied("An active teacher account is required to view class results.")
    membership = ClassMembership.objects.filter(classroom=assignment.classroom, student=request.user).first()
    if not is_teacher and not membership:
        raise PermissionDenied("Join this class to see the assignment.")
    rows = teacher_assignment_rows(assignment) if is_teacher else []
    student_attempts = []
    if membership:
        student_attempts = assignment.attempts.filter(membership=membership).select_related("session")
    return render(request, "classrooms/assignment_detail.html", {
        "assignment": assignment,
        "is_teacher": is_teacher,
        "membership": membership,
        "rows": rows,
        "student_attempts": student_attempts,
    })


@login_required
@require_POST
def start_assignment(request, assignment_id):
    assignment = get_object_or_404(ClassAssignment, pk=assignment_id)
    membership = ClassMembership.objects.filter(classroom=assignment.classroom, student=request.user).first()
    if not membership:
        raise PermissionDenied("Join this class to start its assignment.")
    try:
        session = start_assignment_attempt(assignment_id=assignment.pk, membership=membership)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("classrooms:assignment_detail", assignment_id=assignment.pk)
    return redirect("practice:session_view", session_id=session.pk)
