from django.contrib import admin
from .models import PracticeQuestionResponse, PracticeSession


class PracticeQuestionResponseInline(admin.TabularInline):
    model = PracticeQuestionResponse
    fields = ("order", "question", "selected_option", "is_correct", "time_spent_seconds")
    readonly_fields = ("order", "question", "selected_option", "is_correct", "time_spent_seconds")
    extra = 0
    can_delete = False


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "mode", "paper_type", "score", "percentage", "status", "started_at", "completed_at")
    list_filter = ("mode", "status", "paper_type", "subject")
    search_fields = ("user__username", "user__email", "session_key", "title")
    inlines = [PracticeQuestionResponseInline]
