from django.db.models import Prefetch

from .models import AssignmentAttempt


def teacher_assignment_rows(assignment):
    memberships = assignment.classroom.memberships.select_related("student").prefetch_related(
        Prefetch(
            "attempts",
            queryset=AssignmentAttempt.objects.filter(assignment=assignment).select_related("session"),
            to_attr="assignment_attempts",
        )
    )
    rows = []
    for membership in memberships:
        attempts = membership.assignment_attempts
        completed = [attempt for attempt in attempts if attempt.session.status == attempt.session.Status.COMPLETED]
        best = max(completed, key=lambda attempt: (attempt.session.percentage, attempt.session.completed_at)) if completed else None
        latest = max(attempts, key=lambda attempt: attempt.started_at) if attempts else None
        weak_areas = []
        if best and assignment.kind == assignment.Kind.UTME_MOCK:
            weak_areas = [
                item["subject"].name
                for item in best.session.subject_scores_breakdown
                if item["score_100"] < 60
            ]
        elif best and assignment.topic and best.session.percentage < 60:
            weak_areas = [assignment.topic.name]
        rows.append({
            "membership": membership,
            "student_name": membership.student.get_full_name() or membership.student.username,
            "best_attempt": best,
            "latest_attempt": latest,
            "attempt_count": len(attempts),
            "rank": None,
            "weak_areas": weak_areas,
        })
    rows.sort(key=lambda row: (
        row["best_attempt"] is None,
        -float(row["best_attempt"].session.percentage) if row["best_attempt"] else 0,
        row["student_name"].casefold(),
    ))
    previous_score = None
    previous_rank = None
    for position, row in enumerate(rows, start=1):
        attempt = row["best_attempt"]
        if attempt:
            score = attempt.session.percentage
            if score != previous_score:
                previous_rank = position
                previous_score = score
            row["rank"] = previous_rank
    return rows


def teacher_assignment_snapshot(assignment_id):
    from .models import ClassAssignment

    assignment = ClassAssignment.objects.select_related("classroom").filter(pk=assignment_id).first()
    if not assignment:
        return None
    result = []
    for row in teacher_assignment_rows(assignment):
        best = row["best_attempt"]
        latest = row["latest_attempt"]
        result.append({
            "name": row["student_name"],
            "rank": row["rank"],
            "status": latest.session.get_status_display() if latest else "Not started",
            "late": bool(latest and latest.is_late),
            "score": f"{best.session.percentage:.1f}%" if best else "—",
            "utme_score": f"{best.session.score_out_of_400}/400" if best and assignment.kind == assignment.Kind.UTME_MOCK else "",
            "attempts": row["attempt_count"],
            "weak_areas": row["weak_areas"] or (["No subject below 60%"] if best and assignment.kind == assignment.Kind.UTME_MOCK else []),
        })
    return result
