from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic
from questions.models import Question, Option
from practice.models import PracticeSession, PracticeQuestionResponse


class PracticeTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Chemistry", slug="chemistry", code="CHM")
        self.topic = Topic.objects.create(subject=self.subject, name="Acids and Bases", slug="acids-bases")
        
        self.q1 = Question.objects.create(
            subject=self.subject,
            topic=self.topic,
            exam_type=Question.ExamType.UTME,
            exam_year=2023,
            question_number=1,
            question_text="What is the pH of pure water?",
            explanation="Pure neutral water has a pH of 7 at 25 degrees.",
        )
        self.q1_opt_a = Option.objects.create(question=self.q1, tag="A", text="1", is_correct=False)
        self.q1_opt_b = Option.objects.create(question=self.q1, tag="B", text="5", is_correct=False)
        self.q1_opt_c = Option.objects.create(question=self.q1, tag="C", text="7", is_correct=True)
        self.q1_opt_d = Option.objects.create(question=self.q1, tag="D", text="14", is_correct=False)

    def test_practice_setup_page(self):
        response = self.client.get(reverse("practice:setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configure Your Learning Session")

    def test_start_session_instant_mode(self):
        data = {
            "subject": self.subject.id,
            "mode": "TOPIC_PRACTICE",
            "topic": self.topic.id,
            "question_count": "10",
            "time_limit": "15",
        }
        response = self.client.post(reverse("practice:setup"), data=data)
        self.assertEqual(response.status_code, 302)
        session = PracticeSession.objects.first()
        self.assertIsNotNone(session)
        self.assertEqual(session.mode, PracticeSession.Mode.TOPIC_PRACTICE)
        self.assertEqual(session.responses.count(), 1)

    def test_submit_answer_and_score_session(self):
        # Create session
        session = PracticeSession.objects.create(
            subject=self.subject,
            topic=self.topic,
            mode=PracticeSession.Mode.TOPIC_PRACTICE,
            total_questions=1,
        )
        resp = PracticeQuestionResponse.objects.create(
            session=session,
            question=self.q1,
            order=1,
        )

        # Submit correct answer
        submit_url = reverse("practice:submit_answer", args=[session.id, resp.id])
        res = self.client.post(submit_url, data={"option_id": self.q1_opt_c.id, "time_spent": 10})
        self.assertEqual(res.status_code, 200)
        resp.refresh_from_db()
        self.assertTrue(resp.is_correct)

        # Finish session
        finish_url = reverse("practice:finish_session", args=[session.id])
        fin_res = self.client.post(finish_url, data={"total_time_spent": 15})
        self.assertEqual(fin_res.status_code, 302)
        session.refresh_from_db()
        self.assertTrue(session.is_completed)
        self.assertEqual(session.score, 1)
        self.assertEqual(session.percentage, 100)

        # Check results view
        results_url = reverse("practice:session_results", args=[session.id])
        res_view = self.client.get(results_url)
        self.assertEqual(res_view.status_code, 200)
        self.assertContains(res_view, "Mastery / Distinction")
