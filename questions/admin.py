from django.contrib import admin
from .models import Question, Option


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "topic", "exam_type", "exam_year", "difficulty", "is_published")
    list_filter = ("exam_type", "exam_year", "subject", "difficulty", "is_published")
    search_fields = ("question_text", "explanation")
    inlines = [OptionInline]
