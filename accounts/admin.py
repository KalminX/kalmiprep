from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "target_exam", "target_year", "target_score", "created_at")
    list_filter = ("target_exam", "target_year")
    search_fields = ("user__username", "user__email", "target_course")
