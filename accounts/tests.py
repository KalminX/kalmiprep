from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile
from curriculum.models import Subject
from questions.models import Question
from progress.models import Bookmark

User = get_user_model()


class AccountsTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Mathematics", slug="mathematics", code="MTH")
        self.question = Question.objects.create(
            subject=self.subject,
            exam_type=Question.ExamType.UTME,
            exam_year=2024,
            question_number=1,
            question_text="Sample math question",
        )

    def test_student_registration_and_profile_creation(self):
        reg_data = {
            "first_name": "Kalmin",
            "last_name": "X",
            "username": "kalmin_test",
            "email": "kalmin@example.com",
            "password": "SecurePassword123!",
            "target_exam": "UTME",
        }
        response = self.client.post(reverse("accounts:register"), data=reg_data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="kalmin_test")
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "Kalmin")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.target_exam, "UTME")

    def test_guest_bookmark_migration_on_register(self):
        # Establish session through client request
        self.client.get("/")
        session_key = self.client.session.session_key
        bm = Bookmark.objects.create(session_key=session_key, question=self.question)

        # Register
        reg_data = {
            "first_name": "Student",
            "username": "migrating_student",
            "email": "migrating@example.com",
            "password": "Password123!",
            "target_exam": "WAEC",
        }
        self.client.post(reverse("accounts:register"), data=reg_data)
        user = User.objects.get(username="migrating_student")
        
        bm.refresh_from_db()
        self.assertEqual(bm.user, user)

    def test_login_logout_flow(self):
        user = User.objects.create_user(username="loginuser", password="Password123!")
        # Login
        login_res = self.client.post(reverse("accounts:login"), data={"username": "loginuser", "password": "Password123!"})
        self.assertEqual(login_res.status_code, 302)
        # Logout
        logout_res = self.client.get(reverse("accounts:logout"))
        self.assertEqual(logout_res.status_code, 302)
