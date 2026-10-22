from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic, Subtopic


class CurriculumTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(
            name="Mathematics",
            slug="mathematics",
            description="Pure & Applied Math",
            is_active=True,
            order=1,
        )
        self.topic = Topic.objects.create(
            subject=self.subject,
            name="Algebra",
            slug="algebra",
            description="Polynomials and equations",
            order=1,
        )
        self.subtopic = Subtopic.objects.create(
            topic=self.topic,
            name="Quadratic Equations",
            slug="quadratic-equations",
            order=1,
        )

    def test_curriculum_hierarchy_and_str(self):
        self.assertEqual(str(self.subject), "Mathematics")
        self.assertEqual(str(self.topic), "Mathematics: Algebra")
        self.assertEqual(str(self.subtopic), "Algebra → Quadratic Equations")
        self.assertEqual(self.topic.subtopics.count(), 1)

    def test_subject_list_view(self):
        response = self.client.get(reverse("curriculum:subject_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mathematics")

    def test_subject_detail_view(self):
        response = self.client.get(reverse("curriculum:subject_detail", args=[self.subject.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algebra")

    def test_topic_detail_view(self):
        response = self.client.get(reverse("curriculum:topic_detail", args=[self.subject.slug, self.topic.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quadratic Equations")
