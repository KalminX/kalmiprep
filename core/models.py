import uuid
from django.conf import settings
from django.db import models


class SystemErrorLog(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        ERROR = "ERROR", "Error"
        WARNING = "WARNING", "Warning"
        INFO = "INFO", "Info"

    class Domain(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment & Webhook"
        CBT_EXAM = "CBT_EXAM", "CBT Exam Taking"
        CLIENT_JS = "CLIENT_JS", "Client Browser & KaTeX"
        SYSTEM = "SYSTEM", "Backend System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.ERROR, db_index=True)
    domain = models.CharField(max_length=20, choices=Domain.choices, default=Domain.SYSTEM, db_index=True)
    message = models.CharField(max_length=500)
    stack_trace = models.TextField(blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="error_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "System Error Log"
        verbose_name_plural = "System Error Logs"

    def __str__(self):
        return f"[{self.severity}] [{self.domain}] {self.message[:60]}"
