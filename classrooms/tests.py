from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from curriculum.models import Subject, Topic
from monetization.models import TeacherProfile
from questions.models import Option, Question
from .models import ClassAssignment, ClassMembership, TeachingClass
from .services import join_class, start_assignment_attempt

User = get_user_model()


class ClassroomTests(TestCase):
    def test_student_enrollment_and_assignment_lifecycle(self):
        teacher_user = User.objects.create_user(username="teacher1", password="Password123!")
        teacher = TeacherProfile.objects.create(
            user=teacher_user, kind=TeacherProfile.Kind.TUTOR, display_name="Prof Kalmin", status=TeacherProfile.Status.ACTIVE
        )
        classroom = TeachingClass.objects.create(teacher=teacher, name="Math 101")
        student = User.objects.create_user(username="student1", password="Password123!")

        subject = Subject.objects.create(name="Mathematics", slug="math", code="MTH")
        topic = Topic.objects.create(subject=subject, name="Algebra", slug="algebra")
        q = Question.objects.create(
            subject=subject, topic=topic, exam_type=Question.ExamType.UTME, question_text="Find x"
        )
        Option.objects.create(question=q, tag="A", text="1", is_correct=False)
        opt_b = Option.objects.create(question=q, tag="B", text="2", is_correct=True)

        assignment = ClassAssignment.objects.create(
            classroom=classroom,
            title="Algebra Drill",
            kind=ClassAssignment.Kind.TOPIC_DRILL,
            question_count=1,
            subject=subject,
            topic=topic,
            question_ids=[q.pk],
        )

        # 1. Student joins class by join code
        membership, created = join_class(student=student, join_code=classroom.join_code)
        self.assertTrue(created)
        self.assertEqual(membership.classroom, classroom)

        # 2. Student starts assignment
        session = start_assignment_attempt(assignment_id=assignment.pk, membership=membership)
        self.assertEqual(session.user, student)

        # 3. Student submits answer and finishes session
        resp_obj = session.responses.first()
        self.client.force_login(student)
        submit_url = reverse("practice:submit_answer", args=[session.id, resp_obj.id])
        self.client.post(submit_url, data={"option_id": opt_b.id, "time_spent": 5})

        finish_url = reverse("practice:finish_session", args=[session.id])
        self.client.post(finish_url, data={"total_time_spent": 10})

        session.refresh_from_db()
        self.assertEqual(session.percentage, 100)

        # 4. Results page includes return link to class assignment
        results_view = self.client.get(reverse("practice:session_results", args=[session.id]))
        self.assertEqual(results_view.status_code, 200)
        self.assertContains(results_view, "Class Assignment:")
        self.assertContains(results_view, reverse("classrooms:assignment_detail", args=[assignment.pk]))

        # 5. Teacher views assignment results
        self.client.force_login(teacher_user)
        results_resp = self.client.get(reverse("classrooms:assignment_detail", args=[assignment.pk]))
        self.assertEqual(results_resp.status_code, 200)
        self.assertContains(results_resp, "student1")


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    ALLOWED_HOSTS=["testserver"],
)
class AssignmentResultsWebsocketTests(TransactionTestCase):
    def test_websocket_channel_auth_and_updates(self):
        teacher_user = User.objects.create_user(username="ws_teacher", password="Password123!")
        teacher = TeacherProfile.objects.create(
            user=teacher_user, kind=TeacherProfile.Kind.TUTOR, display_name="WS Teacher", status=TeacherProfile.Status.ACTIVE
        )
        classroom = TeachingClass.objects.create(teacher=teacher, name="WS Class")
        subject = Subject.objects.create(name="WS Chemistry", slug="ws-chem", code="WCH")
        topic = Topic.objects.create(subject=subject, name="WS Topic", slug="ws-topic")
        q = Question.objects.create(
            subject=subject, topic=topic, exam_type=Question.ExamType.UTME, question_text="WS Question"
        )
        Option.objects.create(question=q, tag="A", text="Opt A", is_correct=True)
        assignment = ClassAssignment.objects.create(
            classroom=classroom,
            title="WS Drill",
            kind=ClassAssignment.Kind.TOPIC_DRILL,
            question_count=1,
            subject=subject,
            topic=topic,
            question_ids=[q.pk],
        )

        self.client.force_login(teacher_user)
        self.client.get(reverse("classrooms:assignment_detail", args=[assignment.pk]))
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value

        async def exercise():
            from config.asgi import application

            communicator = WebsocketCommunicator(
                application,
                f"/ws/classrooms/assignments/{assignment.pk}/",
                headers=[(b"cookie", f"{settings.SESSION_COOKIE_NAME}={cookie}".encode()), (b"origin", b"http://testserver")],
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            initial = await communicator.receive_json_from(timeout=3)
            self.assertEqual(initial["type"], "results.updated")
            await communicator.disconnect()

            # Non-owner cannot connect
            other_communicator = WebsocketCommunicator(
                application,
                f"/ws/classrooms/assignments/{assignment.pk}/",
                headers=[(b"origin", b"http://testserver")],
            )
            other_connected, _ = await other_communicator.connect()
            self.assertFalse(other_connected)

        async_to_sync(exercise)()
