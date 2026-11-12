import random

from django.db import IntegrityError, transaction
from django.db.models import Count, Q

from curriculum.models import Subject
from practice.models import PracticeQuestionResponse, PracticeSession
from questions.models import Question

from .models import AssignmentAttempt, ClassAssignment, ClassMembership, TeachingClass


def eligible_questions(queryset):
    return (
        queryset.filter(is_published=True)
        .annotate(
            option_count=Count("options"),
            correct_count=Count("options", filter=Q(options__is_correct=True)),
        )
        .filter(option_count__gte=2, correct_count=1)
        .distinct()
    )


def select_assignment_questions(*, kind, topic=None, question_count=20, electives=None):
    if kind == ClassAssignment.Kind.TOPIC_DRILL:
        pool = eligible_questions(Question.objects.filter(topic=topic, exam_type=Question.ExamType.UTME))
        ids = list(pool.values_list("pk", flat=True))
        if len(ids) < question_count:
            raise ValueError(f"This topic has {len(ids)} eligible UTME questions; {question_count} are required.")
        return random.SystemRandom().sample(ids, question_count)

    english = Subject.objects.filter(slug__in=["english-language", "english"], is_active=True).first()
    if not english:
        raise ValueError("The English Language subject is not available for UTME mocks.")
    if not electives or len(electives) != 3 or english.pk in {subject.pk for subject in electives}:
        raise ValueError("Choose English Language and three different elective subjects.")

    subjects = [english, *electives]
    selected = []
    for subject, target in zip(subjects, [60, 40, 40, 40]):
        ids = list(eligible_questions(Question.objects.filter(
            subject=subject, exam_type=Question.ExamType.UTME
        )).values_list("pk", flat=True))
        if len(ids) < target:
            raise ValueError(
                f"{subject.name} needs {target} eligible UTME questions for a full mock; "
                f"the question bank currently has {len(ids)}."
            )
        selected.extend(random.SystemRandom().sample(ids, target))
    return selected


def create_teaching_class(*, teacher, name):
    for _ in range(5):
        try:
            with transaction.atomic():
                return TeachingClass.objects.create(teacher=teacher, name=name)
        except IntegrityError:
            continue
    raise ValueError("Could not create a unique class code. Please try again.")


@transaction.atomic
def join_class(*, student, join_code):
    classroom = TeachingClass.objects.select_related("teacher").filter(join_code=join_code.upper()).first()
    if not classroom:
        raise ValueError("That class code is not valid.")
    membership, created = ClassMembership.objects.get_or_create(classroom=classroom, student=student)
    return membership, created


@transaction.atomic
def start_assignment_attempt(*, assignment_id, membership):
    membership = ClassMembership.objects.select_for_update().select_related("student").get(pk=membership.pk)
    assignment = ClassAssignment.objects.select_for_update().select_related("classroom").get(pk=assignment_id)
    if assignment.classroom_id != membership.classroom_id:
        raise ValueError("This assignment does not belong to your class.")

    active = AssignmentAttempt.objects.filter(
        assignment=assignment, membership=membership, is_active=True
    ).select_related("session").first()
    if active and active.session.status == PracticeSession.Status.IN_PROGRESS:
        return active.session
    if active:
        active.is_active = False
        active.save(update_fields=["is_active"])

    questions = list(eligible_questions(Question.objects.filter(pk__in=assignment.question_ids)))
    by_id = {question.pk: question for question in questions}
    if len(by_id) != assignment.question_count:
        raise ValueError("Some questions in this assignment are no longer available. Ask the teacher to republish it.")
    ordered_questions = [by_id[question_id] for question_id in assignment.question_ids]
    random.SystemRandom().shuffle(ordered_questions)

    mode = (
        PracticeSession.Mode.JAMB_FULL_MOCK
        if assignment.kind == ClassAssignment.Kind.UTME_MOCK
        else PracticeSession.Mode.TIMED_TEST
    )
    session = PracticeSession.objects.create(
        user=membership.student,
        mode=mode,
        title=assignment.title,
        subject=assignment.subject,
        topic=assignment.topic,
        exam_type=Question.ExamType.UTME,
        total_questions=len(ordered_questions),
        time_limit_seconds=assignment.time_limit_minutes * 60,
        status=PracticeSession.Status.IN_PROGRESS,
    )
    PracticeQuestionResponse.objects.bulk_create([
        PracticeQuestionResponse(session=session, question=question, order=index)
        for index, question in enumerate(ordered_questions, start=1)
    ])
    AssignmentAttempt.objects.create(assignment=assignment, membership=membership, session=session)
    from .realtime import broadcast_assignment_update

    broadcast_assignment_update(assignment.pk)
    return session
