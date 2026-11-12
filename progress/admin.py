from django.contrib import admin
from .models import Bookmark, TopicMastery


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "question", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "session_key", "notes")


@admin.register(TopicMastery)
class TopicMasteryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "topic", "questions_attempted", "questions_correct", "last_practiced_at")
    list_filter = ("topic__subject",)
    search_fields = ("user__username", "session_key", "topic__name")
