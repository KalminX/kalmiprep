from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic
from questions.models import Question, Option
from progress.models import Bookmark


class QuestionsTests(TestCase):
    def test_question_lifecycle_and_bookmark(self):
        subject = Subject.objects.create(name="Physics", slug="physics", code="PHY")
        topic = Topic.objects.create(subject=subject, name="Mechanics", slug="mechanics")
        question = Question.objects.create(
            subject=subject,
            topic=topic,
            exam_type=Question.ExamType.UTME,
            exam_year=2024,
            question_number=1,
            question_text="What is velocity?",
            explanation="Rate of displacement.",
        )
        Option.objects.create(question=question, tag="A", text="Wrong", is_correct=False)
        Option.objects.create(question=question, tag="B", text="Right", is_correct=True)

        self.assertEqual(question.correct_option.label, "B")

        # Question list view and filtering
        resp = self.client.get(reverse("questions:list") + f"?subject={subject.slug}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "velocity")

        # Toggle bookmark
        toggle_url = reverse("questions:toggle_bookmark", args=[question.id])
        self.assertEqual(self.client.post(toggle_url).status_code, 200)
        self.assertTrue(Bookmark.objects.filter(question=question).exists())
