from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic
from questions.models import Question, Option
from progress.models import Bookmark


class QuestionsTests(TestCase):
    def setUp(self):
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
        response = self.client.get(reverse("questions:list") + f"?subject={self.subject.id}&exam_type=UTME")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Physics")

    def test_study_question_view(self):
        response = self.client.get(reverse("questions:study_question", args=[self.question.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Step-by-Step Mathematical Solution")

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
