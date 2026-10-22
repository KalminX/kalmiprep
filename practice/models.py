from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from curriculum.models import Subject, Topic
from questions.models import Question, Option

User = get_user_model()


class PracticeSession(models.Model):
    class Mode(models.TextChoices):
        STUDY = "STUDY", "Self-Paced Study"
        TOPIC_PRACTICE = "TOPIC_PRACTICE", "Interactive Topic Practice (Instant Feedback)"
        TIMED_TEST = "TIMED_TEST", "Timed Topic Assessment"
        CBT_MOCK = "CBT_MOCK", "CBT / Full Mock Examination"
        JAMB_FULL_MOCK = "JAMB_FULL_MOCK", "JAMB Standard UTME Mock (4 Subjects • 180 Qs • 2 Hrs)"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        ABANDONED = "ABANDONED", "Abandoned"

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="practice_sessions")
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    mode = models.CharField(max_length=30, choices=Mode.choices, default=Mode.TOPIC_PRACTICE)
    title = models.CharField(max_length=255, blank=True)
    
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name="practice_sessions")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="practice_sessions")
    exam_type = models.CharField(max_length=20, choices=Question.ExamType.choices, blank=True, null=True)
    
    total_questions = models.PositiveIntegerField(default=0)
    time_limit_seconds = models.PositiveIntegerField(default=0, help_text="Time allowed in seconds (0 for untimed)")
    time_spent_seconds = models.PositiveIntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Practice Session"
        verbose_name_plural = "Practice Sessions"
        indexes = [
            models.Index(fields=["user", "status", "-started_at"], name="idx_sess_user_status"),
            models.Index(fields=["session_key", "status", "-started_at"], name="idx_sess_key_status"),
            models.Index(fields=["mode", "status"], name="idx_sess_mode_status"),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else f"Guest ({self.session_key[:8]})"
        return f"{self.get_mode_display()} — {self.subject or 'Mixed'} ({user_str})"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def expires_at(self):
        """Returns the datetime when this timed session will expire, or None if untimed."""
        if not self.time_limit_seconds:
            return None
        from datetime import timedelta
        return self.started_at + timedelta(seconds=self.time_limit_seconds)

    @property
    def time_remaining_seconds(self):
        """
        Calculates exact seconds remaining based on server-side started_at time.
        Immune to client page refreshes or device clock manipulation.
        """
        if not self.time_limit_seconds:
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = int(self.time_limit_seconds - elapsed)
        return max(0, remaining)

    @property
    def is_expired(self):
        if not self.time_limit_seconds:
            return False
        return self.time_remaining_seconds <= 0

    @property
    def mode_display(self):
        return self.get_mode_display()

    @property
    def answered_count(self):
        return self.responses.filter(selected_option__isnull=False).count()

    @property
    def unanswered_count(self):
        return self.responses.filter(selected_option__isnull=True).count()

    @property
    def correct_count(self):
        return self.responses.filter(is_correct=True).count()

    @property
    def incorrect_count(self):
        return self.responses.filter(selected_option__isnull=False, is_correct=False).count()

    @property
    def flagged_count(self):
        return self.responses.filter(is_flagged=True).count()

    @property
    def score_out_of_400(self):
        """
        Calculates official JAMB UTME aggregate score out of 400 marks.
        In real JAMB UTME, each of the 4 subject components is evaluated out of 100 marks.
        """
        responses = list(self.responses.select_related("question__subject"))
        if not responses:
            return 0
        subject_groups = {}
        for r in responses:
            sid = r.question.subject_id
            if sid not in subject_groups:
                subject_groups[sid] = {"correct": 0, "total": 0}
            subject_groups[sid]["total"] += 1
            if r.is_correct:
                subject_groups[sid]["correct"] += 1

        total_jamb_score = 0.0
        for sid, counts in subject_groups.items():
            if counts["total"] > 0:
                subj_score = (counts["correct"] / counts["total"]) * 100.0
                total_jamb_score += subj_score
        
        # If single subject or generic session, scale percentage to 400
        if len(subject_groups) <= 1:
            return int(round((float(self.percentage) / 100.0) * 400.0))

        return int(round(total_jamb_score))

    @property
    def subject_scores_breakdown(self):
        """Returns subject-by-subject performance analysis for multi-subject mock assessments."""
        responses = list(self.responses.select_related("question__subject"))
        subject_groups = {}
        for r in responses:
            subj = r.question.subject
            if subj.id not in subject_groups:
                subject_groups[subj.id] = {"subject": subj, "correct": 0, "total": 0}
            subject_groups[subj.id]["total"] += 1
            if r.is_correct:
                subject_groups[subj.id]["correct"] += 1

        breakdown = []
        for sid, data in subject_groups.items():
            score_100 = round((data["correct"] / data["total"]) * 100, 1) if data["total"] > 0 else 0
            breakdown.append({
                "subject": data["subject"],
                "score_100": score_100,
                "correct": data["correct"],
                "total": data["total"],
            })
        return breakdown

    @property
    def formatted_time_spent(self):
        mins = self.time_spent_seconds // 60
        secs = self.time_spent_seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def calculate_results(self):
        """Calculates score and percentage, marks session completed, and preserves snapshot."""
        correct = 0
        for resp in self.responses.select_related("selected_option"):
            if resp.selected_option and resp.selected_option.is_correct:
                resp.is_correct = True
                correct += 1
            else:
                resp.is_correct = False
            resp.save(update_fields=["is_correct"])

        self.score = Decimal(str(correct))
        if self.total_questions > 0:
            pct = (Decimal(str(correct)) / Decimal(str(self.total_questions))) * Decimal("100.00")
            self.percentage = round(pct, 2)
        else:
            self.percentage = Decimal("0.00")

        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["score", "percentage", "status", "completed_at", "time_spent_seconds"])
        return self.percentage


class PracticeQuestionResponse(models.Model):
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="practice_responses")
    order = models.PositiveIntegerField(default=1)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("session", "question")
        verbose_name = "Question Response"
        verbose_name_plural = "Question Responses"
        indexes = [
            models.Index(fields=["session", "order"], name="idx_resp_sess_order"),
            models.Index(fields=["session", "is_correct"], name="idx_resp_sess_correct"),
        ]

    def __str__(self):
        opt = self.selected_option.tag if self.selected_option else "Unanswered"
        return f"Session #{self.session_id} Q#{self.order}: {opt}"
