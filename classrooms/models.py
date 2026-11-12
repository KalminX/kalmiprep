import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from curriculum.models import Subject, Topic
from monetization.models import TeacherProfile


def _new_join_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


class TeachingClass(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="classrooms")
    name = models.CharField(max_length=120)
    join_code = models.CharField(max_length=8, unique=True, default=_new_join_code, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "created_at"]

    def __str__(self):
        return f"{self.name} — {self.teacher.display_name}"


class ClassMembership(models.Model):
    classroom = models.ForeignKey(TeachingClass, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["classroom", "student"], name="uniq_classroom_student")]
        ordering = ["joined_at", "pk"]

    def __str__(self):
        return f"{self.student} in {self.classroom}"


class ClassAssignment(models.Model):
    class Kind(models.TextChoices):
        TOPIC_DRILL = "TOPIC_DRILL", "Topic drill"
        UTME_MOCK = "UTME_MOCK", "Full UTME mock"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey(TeachingClass, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=180)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, null=True, blank=True, related_name="class_assignments")
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, null=True, blank=True, related_name="class_assignments")
    elective_subjects = models.ManyToManyField(Subject, blank=True, related_name="utme_class_assignments")
    question_count = models.PositiveSmallIntegerField(default=20)
    time_limit_minutes = models.PositiveSmallIntegerField(default=0, help_text="0 means no time limit")
    due_at = models.DateTimeField(null=True, blank=True)
    question_ids = models.JSONField(default=list, blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.classroom.name}"


class AssignmentAttempt(models.Model):
    assignment = models.ForeignKey(ClassAssignment, on_delete=models.CASCADE, related_name="attempts")
    membership = models.ForeignKey(ClassMembership, on_delete=models.PROTECT, related_name="attempts")
    session = models.OneToOneField(
        "practice.PracticeSession", on_delete=models.CASCADE, related_name="class_assignment_attempt"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "membership"],
                condition=models.Q(is_active=True),
                name="uniq_active_assignment_attempt",
            )
        ]

    def __str__(self):
        return f"{self.membership.student} — {self.assignment.title}"

    @property
    def is_late(self):
        return bool(
            self.assignment.due_at
            and self.session.completed_at
            and self.session.completed_at > self.assignment.due_at
        )
