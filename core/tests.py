import json
from django.test import TestCase, SimpleTestCase
from core.models import SystemErrorLog
from core.templatetags.kalmi_tags import smart_ellipsis, smart_ellipsis_words


class CoreFilterTests(SimpleTestCase):
    def test_smart_ellipsis_formatting(self):
        self.assertEqual(smart_ellipsis(""), "")
        self.assertEqual(smart_ellipsis("Short text", 20), "Short text")
        truncated = smart_ellipsis("Interactive Topic Practice (Instant Feedback)", 20)
        self.assertIn('class="kalmi-smart-ellipsis', truncated)
        self.assertIn("▾", truncated)
        words = smart_ellipsis_words("One two three four five six seven eight nine ten", 5)
        self.assertIn('class="kalmi-smart-ellipsis', words)

    def test_docs_endpoint_status(self):
        resp = self.client.get("/docs/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Teacher &amp; Student Testing Flow")


class SystemErrorLogTelemetryTests(TestCase):
    def test_system_error_log_creation(self):
        log = SystemErrorLog.objects.create(
            severity=SystemErrorLog.Severity.CRITICAL,
            domain=SystemErrorLog.Domain.PAYMENT,
            message="Paystack webhook verification failed",
            stack_trace="Traceback (most recent call last): ...",
            path="/monetization/paystack/webhook/",
            metadata={"reference": "TEST_REF_123"}
        )
        self.assertIsNotNone(log.id)
        self.assertEqual(log.severity, SystemErrorLog.Severity.CRITICAL)
        self.assertEqual(log.domain, SystemErrorLog.Domain.PAYMENT)
        self.assertEqual(SystemErrorLog.objects.count(), 1)

    def test_telemetry_beacon_endpoint_success(self):
        payload = {
            "message": "Uncaught TypeError: Cannot read properties of undefined",
            "stack_trace": "at cbt_exam.html:120:14",
            "path": "/practice/session/42/",
            "domain": "CLIENT_JS",
            "severity": "ERROR",
            "metadata": {"viewport": {"width": 375, "height": 667}}
        }
        resp = self.client.post(
            "/api/telemetry/error-beacon/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(SystemErrorLog.objects.count(), 1)

        logged = SystemErrorLog.objects.first()
        self.assertEqual(logged.domain, SystemErrorLog.Domain.CLIENT_JS)
        self.assertIn("Uncaught TypeError", logged.message)
        self.assertEqual(logged.path, "/practice/session/42/")

    def test_telemetry_beacon_endpoint_invalid_json(self):
        resp = self.client.post(
            "/api/telemetry/error-beacon/",
            data="not-valid-json",
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SystemErrorLog.objects.count(), 0)
