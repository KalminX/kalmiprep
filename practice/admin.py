from django.contrib import admin
from .models import PracticeSession


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "subject", "score", "percentage", "status", "started_at")
    list_filter = ("mode", "status", "subject")
    search_fields = ("user__username", "session_key", "title")
