from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from curriculum.models import Topic
from questions.models import Question

User = get_user_model()


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="bookmarks")
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="bookmarks")
    notes = models.TextField(blank=True, help_text="Personal revision notes on this question")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"

    def __str__(self):
        user_str = self.user.username if self.user else f"Guest ({self.session_key[:8]})"
        return f"Bookmark by {user_str} on Question #{self.question_id}"


class TopicMastery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="topic_masteries")
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="mastery_records")
    questions_attempted = models.PositiveIntegerField(default=0)
    questions_correct = models.PositiveIntegerField(default=0)
    last_practiced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_practiced_at"]
        verbose_name = "Topic Mastery"
        verbose_name_plural = "Topic Masteries"

    def __str__(self):
        user_str = self.user.username if self.user else f"Guest ({self.session_key[:8]})"
        return f"{self.topic.name} Mastery ({self.mastery_percentage}% for {user_str})"

    @property
    def mastery_percentage(self):
        if self.questions_attempted == 0:
            return 0
        return int((self.questions_correct / self.questions_attempted) * 100)

    @property
    def is_weak_topic(self):
        return self.questions_attempted >= 3 and self.mastery_percentage < 60
