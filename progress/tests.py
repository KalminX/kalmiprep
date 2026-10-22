from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic
from questions.models import Question
from progress.models import Bookmark, TopicMastery
from practice.models import PracticeSession


class ProgressTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Mathematics", slug="mathematics", code="MTH")
        self.topic = Topic.objects.create(subject=self.subject, name="Trigonometry", slug="trigonometry")
        self.q = Question.objects.create(
            subject=self.subject,
            topic=self.topic,
            exam_type=Question.ExamType.UTME,
            exam_year=2024,
            question_number=1,
            question_text="Find \\(\\sin(90^\\circ)\\)",
        )

    def test_dashboard_view(self):
        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Learning Space")

    def test_topic_mastery_diagnostic(self):
        # Create mastery record with 5 attempts and only 1 correct (20% -> weak)
        mastery = TopicMastery.objects.create(
            session_key="test-session-key",
            topic=self.topic,
            questions_attempted=5,
            questions_correct=1,
        )
        self.assertEqual(mastery.mastery_percentage, 20)
        self.assertTrue(mastery.is_weak_topic)

    def test_bookmarks_list_view(self):
        # Add bookmark
        s = self.client.session
        s.save()
        Bookmark.objects.create(session_key=s.session_key, question=self.q)

        response = self.client.get(reverse("progress:bookmarks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Saved Questions")
        self.assertContains(response, "Mathematics")
