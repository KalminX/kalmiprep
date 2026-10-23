import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from curriculum.models import Subject, Topic
from practice.models import PracticeQuestionResponse, PracticeSession
from questions.models import Option, Question

MODAL_MARKER = 'id="scientific-calculator-modal"'
CALC_ASSETS = ("js/calculator/engine.js", "js/calculator/ui.js", "vendor/mathlive/mathlive.min.js")


class CalculatorPageRestrictionTests(TestCase):
    """The calculator is rendered ONLY inside active test / practice sessions."""

    def setUp(self):
        self.subject = Subject.objects.create(name="Physics", slug="physics", code="PHY")
        self.topic = Topic.objects.create(subject=self.subject, name="Waves", slug="waves")
        self.question = Question.objects.create(
            subject=self.subject, topic=self.topic, exam_type=Question.ExamType.UTME,
            exam_year=2020, question_number=1, question_text="Frequency of a 17 cm wave at 340 m/s?",
        )
        Option.objects.create(question=self.question, tag="A", text="10Hz", is_correct=False)
        Option.objects.create(question=self.question, tag="B", text="1000Hz", is_correct=True)

    def _session(self, mode, status=PracticeSession.Status.IN_PROGRESS):
        session = PracticeSession.objects.create(
            subject=self.subject, topic=self.topic, mode=mode, total_questions=1, status=status,
        )
        PracticeQuestionResponse.objects.create(session=session, question=self.question, order=1)
        return session

    # ---- supported contexts ----
    def test_calculator_present_in_every_active_session_mode(self):
        for mode in (PracticeSession.Mode.CBT_MOCK, PracticeSession.Mode.TIMED_TEST, PracticeSession.Mode.TOPIC_PRACTICE):
            with self.subTest(mode=mode):
                session = self._session(mode)
                response = self.client.get(reverse("practice:session_view", args=[session.id]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, MODAL_MARKER)
                self.assertContains(response, 'aria-hidden="true"')  # rendered closed
                self.assertContains(response, "toggleCalc()")  # Calc button still wired
                for asset in CALC_ASSETS:
                    self.assertContains(response, asset)

    def test_modal_is_rendered_closed(self):
        session = self._session(PracticeSession.Mode.CBT_MOCK)
        html = self.client.get(reverse("practice:session_view", args=[session.id])).content.decode()
        start = html.index(MODAL_MARKER)
        opening_tag = html[html.rfind("<div", 0, start): html.index(">", start)]
        self.assertIn("hidden", opening_tag)

    def test_modal_markup_is_not_inside_the_answer_form(self):
        """Keypad buttons must never be able to submit an exam answer form."""
        session = self._session(PracticeSession.Mode.CBT_MOCK)
        html = self.client.get(reverse("practice:session_view", args=[session.id])).content.decode()
        modal_pos = html.index(MODAL_MARKER)
        depth = 0
        for token in __import__("re").finditer(r"<(/?)form\b", html[:modal_pos]):
            depth += -1 if token.group(1) else 1
        self.assertEqual(depth, 0, "calculator modal is nested inside a <form>")

    # ---- unsupported contexts ----
    def test_calculator_absent_from_unrelated_pages(self):
        urls = {
            "landing": reverse("core:landing"),
            "dashboard": reverse("progress:dashboard"),
            "ingestion telemetry": reverse("progress:extractor_status"),
            "question library": reverse("questions:list"),
            "study question": reverse("questions:study_question", args=[self.question.pk]),
            "subjects": reverse("curriculum:subject_list"),
            "practice setup": reverse("practice:setup"),
        }
        for name, url in urls.items():
            with self.subTest(page=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, MODAL_MARKER)
                self.assertNotContains(response, "js/calculator/")
                self.assertNotContains(response, "mathlive")

    def test_completed_session_results_page_has_no_calculator(self):
        session = self._session(PracticeSession.Mode.CBT_MOCK, status=PracticeSession.Status.COMPLETED)
        response = self.client.get(reverse("practice:session_results", args=[session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, MODAL_MARKER)

    def test_base_template_does_not_include_calculator_unconditionally(self):
        root = Path(settings.BASE_DIR) / "templates"
        includers = sorted(
            str(p.relative_to(root)) for p in root.rglob("*.html")
            if "components/calculator_modal.html" in p.read_text(encoding="utf-8")
        )
        self.assertEqual(includers, ["practice/cbt_exam.html", "practice/topic_practice.html"])


class CalculatorJavaScriptSuiteTests(TestCase):
    """Runs the Node-based engine and jsdom integration suites as part of `manage.py test`."""

    def _run(self, script):
        node = shutil.which("node")
        root = Path(settings.BASE_DIR)
        if not node or not (root / "node_modules" / "mathjs").exists():
            self.skipTest("node / node_modules not available in this environment")
        if script.endswith("integration.js") and not (root / "node_modules" / "jsdom").exists():
            self.skipTest("jsdom not installed (npm install)")
        proc = subprocess.run([node, str(root / "tests" / script)], capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stdout[-4000:] + proc.stderr[-2000:])

    def test_math_engine_suite(self):
        self._run("test_calculator_engine.js")

    def test_calculator_integration_suite(self):
        self._run("test_calculator_integration.js")
