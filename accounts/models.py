from django.db import models
from django.contrib.auth import get_user_model
from curriculum.models import Subject

User = get_user_model()


class StudentProfile(models.Model):
    class TargetExam(models.TextChoices):
        UTME = "UTME", "UTME / JAMB"
        WAEC = "WAEC", "WAEC / WASSCE"
        NECO = "NECO", "NECO SSCE"
        ALL = "ALL", "All Exam Types"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    target_exam = models.CharField(max_length=20, choices=TargetExam.choices, default=TargetExam.UTME)
    target_year = models.PositiveIntegerField(default=2026)
    target_score = models.PositiveIntegerField(default=300, help_text="e.g. 300+ for JAMB, 8 A's for WAEC")
    target_course = models.CharField(max_length=150, blank=True, help_text="e.g. Medicine, Computer Science, Engineering")
    preferred_subjects = models.ManyToManyField(Subject, blank=True, related_name="students")
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.get_target_exam_display()})"
