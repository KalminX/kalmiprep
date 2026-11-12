from django.test import TestCase
from django.urls import reverse
from curriculum.models import Subject, Topic
from questions.models import Question, Option
from practice.models import PracticeSession, PracticeQuestionResponse


class PracticeTests(TestCase):
    def test_practice_session_lifecycle(self):
        subject = Subject.objects.create(name="Chemistry", slug="chemistry", code="CHM")
        topic = Topic.objects.create(subject=subject, name="Acids and Bases", slug="acids-bases")
        q1 = Question.objects.create(
            subject=subject,
            topic=topic,
            exam_type=Question.ExamType.UTME,
            exam_year=2023,
            question_number=1,
            question_text="What is the pH of pure water?",
            explanation="Pure neutral water has a pH of 7.",
        )
        Option.objects.create(question=q1, tag="A", text="1", is_correct=False)
        opt_correct = Option.objects.create(question=q1, tag="C", text="7", is_correct=True)

        # 1. Setup page renders
        setup_resp = self.client.get(reverse("practice:setup"))
        self.assertEqual(setup_resp.status_code, 200)

        # 2. Start session
        session = PracticeSession.objects.create(
            subject=subject,
            topic=topic,
            mode=PracticeSession.Mode.TOPIC_PRACTICE,
            total_questions=1,
        )
        resp_obj = PracticeQuestionResponse.objects.create(
            session=session,
            question=q1,
            order=1,
        )

        # 3. Submit answer
        submit_url = reverse("practice:submit_answer", args=[session.id, resp_obj.id])
        submit_res = self.client.post(submit_url, data={"option_id": opt_correct.id, "time_spent": 10})
        self.assertEqual(submit_res.status_code, 200)

        # 4. Finish session and verify scoring
        finish_url = reverse("practice:finish_session", args=[session.id])
        finish_res = self.client.post(finish_url, data={"total_time_spent": 15})
        self.assertEqual(finish_res.status_code, 302)

        session.refresh_from_db()
        self.assertTrue(session.is_completed)
        self.assertEqual(session.score, 1)
        self.assertEqual(session.percentage, 100)

        results_url = reverse("practice:session_results", args=[session.id])
        self.assertEqual(self.client.get(results_url).status_code, 200)
