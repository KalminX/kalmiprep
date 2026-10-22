from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from curriculum.models import Subject, Topic
from questions.models import Question, Option
from progress.models import Bookmark


class QuestionsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.subject = Subject.objects.create(name="Physics", slug="physics", code="PHY")
        self.topic = Topic.objects.create(subject=self.subject, name="Mechanics", slug="mechanics")
        self.question = Question.objects.create(
            subject=self.subject,
            topic=self.topic,
            exam_type=Question.ExamType.UTME,
            exam_year=2024,
            question_number=1,
            question_text="What is the unit of velocity? \\(v = \\frac{d}{t}\\)",
            explanation="Velocity is rate of change of displacement in \\(m/s\\).",
        )
        self.opt_a = Option.objects.create(question=self.question, tag="A", text="\\(m/s^2\\)", is_correct=False)
        self.opt_b = Option.objects.create(question=self.question, tag="B", text="\\(m/s\\)", is_correct=True)
        self.opt_c = Option.objects.create(question=self.question, tag="C", text="\\(kg\\)", is_correct=False)
        self.opt_d = Option.objects.create(question=self.question, tag="D", text="\\(N\\)", is_correct=False)

    def test_question_model_and_options(self):
        self.assertEqual(self.question.options.count(), 4)
        self.assertEqual(self.question.correct_option.label, "B")
        self.assertTrue(self.question.has_solution)

    def test_question_list_view(self):
        response = self.client.get(reverse("questions:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Physics")
        self.assertContains(response, "unit of velocity")

    def test_question_library_filters(self):
        # 1. Filter by numeric subject ID
        response = self.client.get(reverse("questions:list") + f"?subject={self.subject.id}&exam_type=UTME")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Physics")

        # 2. Filter by subject SLUG (e.g. ?subject=physics)
        slug_response = self.client.get(reverse("questions:list") + f"?subject={self.subject.slug}")
        self.assertEqual(slug_response.status_code, 200)
        self.assertContains(slug_response, "Physics")
        self.assertContains(slug_response, "unit of velocity")

        # 3. Filter by other subject slug shouldn't show Physics questions
        math_subject = Subject.objects.create(name="Mathematics", slug="mathematics", code="MTH")
        math_response = self.client.get(reverse("questions:list") + f"?subject=mathematics")
        self.assertEqual(math_response.status_code, 200)
        self.assertNotContains(math_response, "unit of velocity")

        # 4. Filter by exam alias (?exam=UTME)
        exam_alias_resp = self.client.get(reverse("questions:list") + "?exam=UTME")
        self.assertEqual(exam_alias_resp.status_code, 200)
        self.assertContains(exam_alias_resp, "Physics")

    def test_study_question_view(self):
        response = self.client.get(reverse("questions:study_question", args=[self.question.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unit of velocity")

    def test_bookmark_toggle_htmx(self):
        url = reverse("questions:toggle_bookmark", args=[self.question.id])
        # Add bookmark
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Bookmark.objects.filter(question=self.question).exists())

        # Toggle to remove bookmark
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 200)
        self.assertFalse(Bookmark.objects.filter(question=self.question).exists())

    def test_search_filter_and_highlighting(self):
        # Test full-text / keyword search in question list
        response = self.client.get(reverse("questions:list") + "?search=velocity")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<mark")
        self.assertContains(response, "velocity</mark>")
        # Ensure LaTeX formula delimiter is still intact
        self.assertContains(response, "\\(v = \\frac{d}{t}\\)")

        # Test highlighting in study view
        study_resp = self.client.get(reverse("questions:study_question", args=[self.question.id]) + "?search=velocity")
        self.assertEqual(study_resp.status_code, 200)
        self.assertContains(study_resp, "<mark")
        self.assertContains(study_resp, "velocity</mark>")

        # Test auto-open solution drawer when searched keyword is in the explanation
        # "displacement" is in explanation -> drawer should be open ("Hide Solution")
        disp_resp = self.client.get(reverse("questions:list") + "?search=displacement")
        self.assertEqual(disp_resp.status_code, 200)
        self.assertContains(disp_resp, "Hide Solution")
        self.assertContains(disp_resp, f'id="solution-drawer-{self.question.id}" class=" mt-3')

        # "unit" is only in question text, NOT in explanation -> drawer should stay collapsed
        unit_resp = self.client.get(reverse("questions:list") + "?search=unit")
        self.assertEqual(unit_resp.status_code, 200)
        self.assertContains(unit_resp, f'id="solution-drawer-{self.question.id}" class="hidden mt-3')

