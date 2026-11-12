from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic
from progress.models import TopicMastery


class ProgressTests(TestCase):
    def test_progress_dashboard_and_mastery(self):
        subject = Subject.objects.create(name="Mathematics", slug="mathematics", code="MTH")
        topic = Topic.objects.create(subject=subject, name="Trigonometry", slug="trigonometry")

        mastery = TopicMastery.objects.create(
            session_key="test-key",
            topic=topic,
            questions_attempted=5,
            questions_correct=1,
        )
        self.assertEqual(mastery.mastery_percentage, 20)
        self.assertTrue(mastery.is_weak_topic)

        resp = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(resp.status_code, 200)
