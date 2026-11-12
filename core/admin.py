from django.contrib import admin
from .models import SystemErrorLog


@admin.register(SystemErrorLog)
class SystemErrorLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "severity", "domain", "message", "path", "user", "ip_address")
    list_filter = ("severity", "domain", "timestamp")
    search_fields = ("message", "stack_trace", "path", "ip_address")
    readonly_fields = ("id", "timestamp", "severity", "domain", "message", "stack_trace", "path", "user", "ip_address", "metadata")

    def has_add_permission(self, request):
        return False
