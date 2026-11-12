from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic, Subtopic


class CurriculumTests(TestCase):
    def test_curriculum_hierarchy_and_views(self):
        subject = Subject.objects.create(name="Mathematics", slug="mathematics", code="MTH")
        topic = Topic.objects.create(subject=subject, name="Algebra", slug="algebra")
        subtopic = Subtopic.objects.create(topic=topic, name="Quadratics", slug="quadratics")

        self.assertEqual(str(subject), "Mathematics")
        self.assertEqual(str(topic), "Mathematics: Algebra")
        self.assertEqual(str(subtopic), "Algebra → Quadratics")

        list_resp = self.client.get(reverse("curriculum:subject_list"))
        self.assertEqual(list_resp.status_code, 200)

        detail_resp = self.client.get(reverse("curriculum:subject_detail", args=[subject.slug]))
        self.assertEqual(detail_resp.status_code, 200)
