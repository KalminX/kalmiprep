from django.contrib import admin

from .models import AssignmentAttempt, ClassAssignment, ClassMembership, TeachingClass


@admin.register(TeachingClass)
class TeachingClassAdmin(admin.ModelAdmin):
    list_display = ("name", "teacher", "join_code", "created_at")
    search_fields = ("name", "teacher__display_name", "join_code")
    readonly_fields = ("id", "join_code", "created_at")


@admin.register(ClassMembership)
class ClassMembershipAdmin(admin.ModelAdmin):
    list_display = ("classroom", "student", "joined_at")
    search_fields = ("classroom__name", "student__username", "student__first_name", "student__last_name")
    readonly_fields = tuple(field.name for field in ClassMembership._meta.fields)


@admin.register(ClassAssignment)
class ClassAssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "kind", "question_count", "due_at", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("title", "classroom__name", "classroom__teacher__display_name")
    readonly_fields = tuple(field.name for field in ClassAssignment._meta.fields)


@admin.register(AssignmentAttempt)
class AssignmentAttemptAdmin(admin.ModelAdmin):
    list_display = ("assignment", "membership", "session", "started_at", "is_active")
    readonly_fields = tuple(field.name for field in AssignmentAttempt._meta.fields)
