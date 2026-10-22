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

    def test_start_session_timed_mode_custom_minutes(self):
        data = {
            "subject": self.subject.id,
            "mode": "TIMED_TEST",
            "topic": self.topic.id,
            "question_count": "10",
            "time_limit_minutes": "25",
        }
        response = self.client.post(reverse("practice:setup"), data=data)
        self.assertEqual(response.status_code, 302)
        session = PracticeSession.objects.filter(mode=PracticeSession.Mode.TIMED_TEST).first()
        self.assertIsNotNone(session)
        # 25 minutes = 1500 seconds
        self.assertEqual(session.time_limit_seconds, 1500)

    def test_time_sync_endpoint_and_timer_persistence(self):
        from django.utils import timezone
        from datetime import timedelta
        
        # Session started 2 minutes (120 seconds) ago with a 10-minute (600 seconds) limit
        two_mins_ago = timezone.now() - timedelta(seconds=120)
        session = PracticeSession.objects.create(
            subject=self.subject,
            topic=self.topic,
            mode=PracticeSession.Mode.TIMED_TEST,
            total_questions=1,
            time_limit_seconds=600,
            started_at=two_mins_ago,
        )

        # Remaining time should be approximately 480 seconds (between 475 and 480)
        self.assertAlmostEqual(session.time_remaining_seconds, 480, delta=3)
        self.assertFalse(session.is_expired)

        # Sync endpoint returns correct remaining seconds
        sync_url = reverse("practice:time_sync", args=[session.id])
        res = self.client.get(sync_url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_expired"])
        self.assertAlmostEqual(data["remaining_seconds"], 480, delta=3)

    def test_timer_expiration_auto_completion(self):
        from django.utils import timezone
        from datetime import timedelta

        # Session started 20 minutes ago with a 15-minute limit (expired 5 minutes ago)
        twenty_mins_ago = timezone.now() - timedelta(minutes=20)
        session = PracticeSession.objects.create(
            subject=self.subject,
            topic=self.topic,
            mode=PracticeSession.Mode.TIMED_TEST,
            total_questions=1,
            time_limit_seconds=900,
            started_at=twenty_mins_ago,
        )

        self.assertTrue(session.is_expired)
        self.assertEqual(session.time_remaining_seconds, 0)

        # Accessing session_view when expired should auto-complete and redirect to results
        view_url = reverse("practice:session_view", args=[session.id])
        res = self.client.get(view_url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(f"/practice/session/{session.id}/results/", res.url)

        session.refresh_from_db()
        self.assertTrue(session.is_completed)
        self.assertEqual(session.time_spent_seconds, 900)

    def test_jamb_full_mock_setup_and_scoring(self):
        # Create second subject
        math_subj = Subject.objects.create(name="Mathematics", slug="mathematics", code="MTH")
        q_math = Question.objects.create(
            subject=math_subj,
            exam_type=Question.ExamType.UTME,
            exam_year=2023,
            question_number=2,
            question_text="Solve 2x = 10",
            explanation="x = 5",
        )
        opt_correct = Option.objects.create(question=q_math, tag="A", text="5", is_correct=True)

        # Launch JAMB Full Mock session
        data = {
            "mode": "JAMB_FULL_MOCK",
            "electives": [self.subject.id, math_subj.id],
        }
        res = self.client.post(reverse("practice:setup"), data=data)
        self.assertEqual(res.status_code, 302)

        session = PracticeSession.objects.filter(mode=PracticeSession.Mode.JAMB_FULL_MOCK).first()
        self.assertIsNotNone(session)
        # JAMB standard duration: 2 hours = 7200 seconds
        self.assertEqual(session.time_limit_seconds, 7200)
        self.assertGreater(session.total_questions, 0)

        # Verify score_out_of_400 calculation
        session.calculate_results()
        self.assertIsInstance(session.score_out_of_400, int)
        self.assertGreaterEqual(session.score_out_of_400, 0)
        self.assertLessEqual(session.score_out_of_400, 400)
