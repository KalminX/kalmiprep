from urllib.parse import urlsplit
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from curriculum.models import Subject, Topic
from practice.models import PracticeSession
from questions.models import Option, Question
from .models import (
    PaidTest,
    TeacherProfile,
    TeacherWallet,
    TestPurchase,
    TeacherInvitation,
    WalletEntry,
)
from .services import (
    access_pin_for,
    record_verified_payment,
    split_price,
    start_paid_test_attempt,
)

User = get_user_model()


@override_settings(
    PAYSTACK_SECRET_KEY="sk_test_unit",
    PAYSTACK_TEST_MODE=True,
    PAID_TEST_PIN_SECRET="unit-test-pin-secret",
    SITE_URL="https://kalmiprep.test",
    SECRET_KEY="unit-test-secret",
)
class MonetizationTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Mathematics", slug="math", code="MTH")
        self.topic = Topic.objects.create(subject=self.subject, name="Algebra", slug="algebra")
        self.teacher_user = User.objects.create_user(username="prof_ada", password="Password123!", email="ada@example.com")
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user,
            kind=TeacherProfile.Kind.TUTOR,
            display_name="Ada Math",
            status=TeacherProfile.Status.ACTIVE,
        )
        self.wallet = TeacherWallet.objects.create(teacher=self.teacher)
        self.question = Question.objects.create(
            subject=self.subject,
            topic=self.topic,
            exam_type=Question.ExamType.GENERAL,
            question_number=1,
            question_text="Solve x + 1 = 2",
        )
        Option.objects.create(question=self.question, tag="A", text="0", is_correct=False)
        Option.objects.create(question=self.question, tag="B", text="1", is_correct=True)

        self.paid_test = PaidTest.objects.create(
            teacher=self.teacher,
            title="Algebra Drill",
            price_kobo=20000,
            question_count=1,
            time_limit_minutes=20,
            randomization=PaidTest.Randomization.SHARED_SET,
            fixed_question_ids=[self.question.pk],
            is_published=True,
        )
        self.paid_test.topics.add(self.topic)
        self.buyer = User.objects.create_user(username="student_buyer", password="Password123!", email="buyer@example.com")

    def test_payment_verification_and_wallet_crediting(self):
        # 1. Price splitting
        teacher_cut, platform_cut = split_price(20000)
        self.assertEqual(teacher_cut + platform_cut, 20000)
        self.assertEqual(teacher_cut, 16000)

        # 2. Record purchase
        purchase = TestPurchase.objects.create(
            test=self.paid_test,
            teacher=self.teacher,
            buyer=self.buyer,
            buyer_name="Student Buyer",
            buyer_email="buyer@example.com",
            amount_kobo=20000,
            teacher_share_kobo=teacher_cut,
            platform_share_kobo=platform_cut,
            paystack_reference="REF-test-123",
        )

        # 3. Record verified payment
        receipt_data = {
            "status": "success",
            "reference": purchase.paystack_reference,
            "amount": 20000,
            "currency": "NGN",
            "id": 998877,
        }
        record_verified_payment(purchase.paystack_reference, receipt_data)

        purchase.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(purchase.status, TestPurchase.Status.PAID)
        self.assertEqual(self.wallet.balance_kobo, 16000)

        # Email PIN delivery verified
        self.assertTrue(len(mail.outbox) >= 1)
        self.assertIn("Test Access PIN", mail.outbox[0].subject)
        self.assertIn(purchase.buyer_email, mail.outbox[0].to)

        # 4. Idempotency on repeat
        record_verified_payment(purchase.paystack_reference, receipt_data)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_kobo, 16000)
        self.assertEqual(WalletEntry.objects.filter(source_reference=f"paystack:{purchase.paystack_reference}").count(), 1)

    def test_pin_access_starts_paid_attempt(self):
        purchase = TestPurchase.objects.create(
            test=self.paid_test,
            teacher=self.teacher,
            buyer=self.buyer,
            buyer_name="Student Buyer",
            buyer_email="buyer@example.com",
            amount_kobo=20000,
            teacher_share_kobo=16000,
            platform_share_kobo=4000,
            paystack_reference="REF-pin-test",
            status=TestPurchase.Status.PAID,
        )
        pin = access_pin_for(purchase)
        from .services import pin_hash
        purchase.access_pin_hash = pin_hash(pin)
        purchase.save(update_fields=["access_pin_hash"])
        self.assertEqual(len(pin), 10)

        session = start_paid_test_attempt(purchase)
        self.assertEqual(session.total_questions, 1)

        # Unauthenticated request without session grant is forbidden
        resp = self.client.get(reverse("practice:session_view", args=[session.id]))
        self.assertEqual(resp.status_code, 403)

    def test_staff_teacher_invitation_lifecycle(self):
        staff_user = User.objects.create_superuser(username="admin_user", password="Password123!", email="admin@kalmiprep.test")
        self.client.force_login(staff_user)

        resp = self.client.post(reverse("monetization:invite_teacher"), {
            "email": "invited_teacher@example.com",
            "kind": TeacherProfile.Kind.TUTOR,
            "display_name": "Invited Tutor",
        })
        self.assertRedirects(resp, reverse("monetization:invite_teacher"))
        self.assertEqual(len(mail.outbox), 1)

        invitation = TeacherInvitation.objects.get(email="invited_teacher@example.com")
        link = next(line for line in mail.outbox[0].body.splitlines() if "/monetization/invitations/" in line)
        path = urlsplit(link).path

        self.client.logout()
        # Accept invite and create account
        reg_resp = self.client.post(path, {
            "username": "new_teacher_acc",
            "first_name": "New",
            "last_name": "Teacher",
            "password": "Password123!",
        })
        self.assertRedirects(reg_resp, reverse("monetization:teacher_onboarding"))
        user = User.objects.get(username="new_teacher_acc")
        self.assertEqual(user.teacher_profile.status, TeacherProfile.Status.ACTIVE)

    def test_demo_payment_bypass_and_instant_verification(self):
        resp = self.client.post(reverse("monetization:public_test", args=[self.paid_test.share_code]), {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "08099887766",
            "payment_mode": "demo",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("monetization:paystack_callback"), resp.url)

        purchase = TestPurchase.objects.get(buyer_email="jane@example.com")
        self.assertEqual(purchase.status, TestPurchase.Status.PAID)
        self.assertEqual(purchase.amount_kobo, 20000)
        self.assertEqual(purchase.teacher_share_kobo, 16000)
        self.assertEqual(purchase.platform_share_kobo, 4000)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_kobo, 16000)

    def test_teacher_start_approval_gate_and_waiting_room(self):
        self.paid_test.requires_approval = True
        self.paid_test.is_approved_for_start = False
        self.paid_test.save()

        purchase = TestPurchase.objects.create(
            test=self.paid_test,
            teacher=self.teacher,
            buyer=self.buyer,
            buyer_name="Student Test",
            buyer_email="student@example.com",
            amount_kobo=20000,
            teacher_share_kobo=16000,
            platform_share_kobo=4000,
            paystack_reference="REF-gate-test",
            status=TestPurchase.Status.PAID,
        )
        pin = access_pin_for(purchase)
        from .services import pin_hash
        purchase.access_pin_hash = pin_hash(pin)
        purchase.save(update_fields=["access_pin_hash"])

        # 1. Student enters PIN while locked -> Redirected to waiting room
        enter_resp = self.client.post(
            reverse("monetization:enter_test", args=[self.paid_test.share_code]),
            {"pin": pin},
        )
        self.assertRedirects(
            enter_resp,
            reverse("monetization:waiting_room", args=[self.paid_test.share_code]),
        )

        # 2. Check status polling returns 200 without HX-Redirect when locked
        status_resp = self.client.get(reverse("monetization:check_test_started", args=[self.paid_test.share_code]))
        self.assertEqual(status_resp.status_code, 200)
        self.assertNotIn("HX-Redirect", status_resp.headers)

        # 3. Teacher unlocks exam
        self.client.force_login(self.teacher_user)
        approve_resp = self.client.post(reverse("monetization:approve_test_start", args=[self.paid_test.share_code]))
        self.assertRedirects(approve_resp, reverse("monetization:test_leaderboard", args=[self.paid_test.share_code]))
        self.paid_test.refresh_from_db()
        self.assertTrue(self.paid_test.is_approved_for_start)

        # 4. Check status polling now responds with HX-Redirect header
        self.client.logout()
        status_resp2 = self.client.get(reverse("monetization:check_test_started", args=[self.paid_test.share_code]))
        self.assertEqual(status_resp2.status_code, 200)
        self.assertIn("HX-Redirect", status_resp2.headers)

    def test_staff_admin_earnings_and_teacher_approval(self):
        staff_user = User.objects.create_superuser(username="admin_earnings_user", password="Password123!", email="admin_earn@example.com")
        self.client.force_login(staff_user)

        # Access admin earnings
        resp = self.client.get(reverse("monetization:admin_earnings"))
        self.assertEqual(resp.status_code, 200)

        # Create pending teacher
        applicant_user = User.objects.create_user(username="pending_applicant", password="Password123!", email="applicant@example.com")
        pending_teacher = TeacherProfile.objects.create(
            user=applicant_user,
            kind=TeacherProfile.Kind.TUTOR,
            display_name="Applicant Tutor",
            status=TeacherProfile.Status.PENDING,
        )

        approve_resp = self.client.post(reverse("monetization:approve_teacher", args=[pending_teacher.id]))
        self.assertRedirects(approve_resp, reverse("monetization:admin_earnings"))
        pending_teacher.refresh_from_db()
        self.assertEqual(pending_teacher.status, TeacherProfile.Status.ACTIVE)
        self.assertTrue(hasattr(pending_teacher, "wallet"))


class TeacherStudentFullLifecycleTestCase(TestCase):
    """
    Simulates the complete end-to-end Teacher & Student workflow demonstrated in the video streams,
    exercising all 12 checkpoints without any video recording or media overhead.
    """
    def setUp(self):
        self.subject = Subject.objects.create(name="Chemistry", slug="chemistry", code="CHM")
        self.topic1 = Topic.objects.create(subject=self.subject, name="Atomic Structure", slug="atomic-structure")
        self.topic2 = Topic.objects.create(subject=self.subject, name="Chemical Bonding", slug="chemical-bonding")

        # Create 5 chemistry questions with verified correct options
        self.questions = []
        self.correct_options = []
        for i in range(1, 6):
            q = Question.objects.create(
                subject=self.subject,
                topic=self.topic1 if i <= 3 else self.topic2,
                exam_type=Question.ExamType.UTME,
                exam_year=2024,
                question_number=i,
                question_text=f"Question {i}: Chemistry examination problem text.",
                explanation=f"Solution for question {i}.",
            )
            # Create 4 options A, B, C, D
            correct_tag = "B" if i != 2 else "A"
            for tag in ["A", "B", "C", "D"]:
                opt = Option.objects.create(
                    question=q,
                    tag=tag,
                    text=f"Option {tag} content",
                    is_correct=(tag == correct_tag),
                )
                if tag == correct_tag:
                    self.correct_options.append(opt)
            self.questions.append(q)

        # Teacher User & Profile
        self.teacher_user = User.objects.create_user(
            username="demo_teacher_lifecycle",
            password="Password123!",
            email="teacher@kalmiprep.test",
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user,
            kind=TeacherProfile.Kind.TUTOR,
            display_name="Demo Teacher",
            status=TeacherProfile.Status.ACTIVE,
        )
        self.wallet = TeacherWallet.objects.create(teacher=self.teacher)

        # Student User
        self.student_user = User.objects.create_user(
            username="student_chinedu",
            password="Password123!",
            email="chinedu@kalmiprep.test",
        )

    def test_full_teacher_student_lifecycle_without_video(self):
        from django.test import Client
        teacher_client = Client()
        teacher_client.force_login(self.teacher_user)
        student_client = Client()
        student_client.force_login(self.student_user)

        # -------------------------------------------------------------
        # CHECKPOINT 1: Teacher creates Paid Test with Proctor Gate
        # -------------------------------------------------------------
        create_resp = teacher_client.post(
            reverse("monetization:create_test"),
            data={
                "title": "JAMB Chemistry Mock Test (Verified)",
                "price_naira": "1500.00",
                "question_count": 5,
                "time_limit_minutes": 30,
                "randomization": PaidTest.Randomization.SHARED_SET,
                "requires_approval": "on",
                "topics": [self.topic1.id, self.topic2.id],
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        paid_test = PaidTest.objects.filter(teacher=self.teacher).latest("created_at")
        self.assertEqual(paid_test.price_kobo, 150000)
        self.assertTrue(paid_test.requires_approval)
        self.assertFalse(paid_test.is_approved_for_start)
        self.assertTrue(bool(paid_test.share_code))

        # -------------------------------------------------------------
        # CHECKPOINT 2: Student Discovers Test & Performs Demo Checkout
        # -------------------------------------------------------------
        public_url = reverse("monetization:public_test", args=[paid_test.share_code])
        landing_resp = student_client.get(public_url)
        self.assertEqual(landing_resp.status_code, 200)

        # Student posts checkout data
        teacher_cut, platform_cut = split_price(150000)
        self.assertEqual(teacher_cut, 120000)
        self.assertEqual(platform_cut, 30000)

        purchase = TestPurchase.objects.create(
            test=paid_test,
            teacher=self.teacher,
            buyer=self.student_user,
            buyer_name="Chinedu Okafor",
            buyer_email="chinedu@kalmiprep.test",
            amount_kobo=150000,
            teacher_share_kobo=teacher_cut,
            platform_share_kobo=platform_cut,
            paystack_reference=f"REF-E2E-{str(paid_test.share_code)[:8]}",
            status=TestPurchase.Status.PENDING,
        )

        # Instant demo payment verification
        record_verified_payment(purchase.paystack_reference, {
            "status": "success",
            "reference": purchase.paystack_reference,
            "amount": 150000,
            "currency": "NGN",
        })
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, TestPurchase.Status.PAID)

        # Generate verified access PIN
        from .services import pin_hash
        pin = access_pin_for(purchase)
        purchase.access_pin_hash = pin_hash(pin)
        purchase.save(update_fields=["access_pin_hash"])
        self.assertEqual(len(pin), 10)

        # -------------------------------------------------------------
        # CHECKPOINT 3: Student Enters Test & Held in Waiting Room
        # -------------------------------------------------------------
        enter_resp = student_client.post(
            reverse("monetization:enter_test", args=[paid_test.share_code]),
            {"pin": pin},
        )
        self.assertRedirects(
            enter_resp,
            reverse("monetization:waiting_room", args=[paid_test.share_code]),
        )

        # Attempt to access session is gated
        session = start_paid_test_attempt(purchase)
        self.assertEqual(session.total_questions, 5)

        # -------------------------------------------------------------
        # CHECKPOINT 4: Real-Time Waiting Room Polling (Locked)
        # -------------------------------------------------------------
        poll_locked = student_client.get(reverse("monetization:check_test_started", args=[paid_test.share_code]))
        self.assertEqual(poll_locked.status_code, 200)
        self.assertNotIn("HX-Redirect", poll_locked.headers)

        # -------------------------------------------------------------
        # CHECKPOINT 5: Teacher Proctor Unlocks Exam
        # -------------------------------------------------------------
        approve_resp = teacher_client.post(reverse("monetization:approve_test_start", args=[paid_test.share_code]))
        self.assertEqual(approve_resp.status_code, 302)
        paid_test.refresh_from_db()
        self.assertTrue(paid_test.is_approved_for_start)

        # -------------------------------------------------------------
        # CHECKPOINT 6: Student Waiting Room Auto-Redirects on Unlock
        # -------------------------------------------------------------
        poll_unlocked = student_client.get(reverse("monetization:check_test_started", args=[paid_test.share_code]))
        self.assertEqual(poll_unlocked.status_code, 200)
        self.assertIn("HX-Redirect", poll_unlocked.headers)

        # Grant session ownership to student_client session
        s = student_client.session
        s[f"paid_test_session_{session.id}"] = True
        s.save()

        # -------------------------------------------------------------
        # CHECKPOINT 7 & 8: Student Answers 5 Questions (4 Correct, 1 Target Incorrect)
        # -------------------------------------------------------------
        responses = list(session.responses.order_by("order"))
        self.assertEqual(len(responses), 5)

        for idx, resp_obj in enumerate(responses):
            q = resp_obj.question
            if idx < 4:
                # Select correct option (Mastery)
                chosen_opt = q.options.filter(is_correct=True).first()
            else:
                # Select incorrect option (Deliberate Practice)
                chosen_opt = q.options.filter(is_correct=False).first()

            submit_url = reverse("practice:submit_answer", args=[session.id, resp_obj.id])
            ans_res = student_client.post(submit_url, {"option_id": chosen_opt.id, "time_spent": 12})
            self.assertEqual(ans_res.status_code, 200)

        # Submit final exam
        finish_url = reverse("practice:finish_session", args=[session.id])
        finish_res = student_client.post(finish_url, {"total_time_spent": 60})
        self.assertEqual(finish_res.status_code, 302)

        # -------------------------------------------------------------
        # CHECKPOINT 9: Accurate Distinction Scoring (4 / 5 = 80%)
        # -------------------------------------------------------------
        session.refresh_from_db()
        self.assertTrue(session.is_completed)
        self.assertEqual(session.score, 4)
        self.assertEqual(session.total_questions, 5)
        self.assertEqual(session.percentage, 80)

        # Results page view check
        results_url = reverse("practice:session_results", args=[session.id])
        results_resp = student_client.get(results_url)
        self.assertEqual(results_resp.status_code, 200)
        self.assertContains(results_resp, "4 / 5")
        self.assertContains(results_resp, "80%")

        # -------------------------------------------------------------
        # CHECKPOINT 10: Teacher Proctor Leaderboard Synchronization
        # -------------------------------------------------------------
        leaderboard_url = reverse("monetization:test_leaderboard", args=[paid_test.share_code])
        lb_resp = teacher_client.get(leaderboard_url)
        self.assertEqual(lb_resp.status_code, 200)
        self.assertContains(lb_resp, "Chinedu Okafor")
        self.assertContains(lb_resp, "80.0%")
        self.assertContains(lb_resp, "4/5")

        # -------------------------------------------------------------
        # CHECKPOINT 11 & 12: Teacher Wallet Balance & Platform Commission
        # -------------------------------------------------------------
        self.wallet.refresh_from_db()
        # Exactly 80% of ₦1,500 = ₦1,200 (120,000 kobo)
        self.assertEqual(self.wallet.balance_kobo, 120000)
        self.assertEqual(self.wallet.balance_naira, 1200)
        self.assertEqual(purchase.teacher_share_kobo, 120000)
        self.assertEqual(purchase.platform_share_kobo, 30000)

