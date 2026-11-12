from monetization.access import can_access_practice_session as can_access_paid_session


def can_access_practice_session(request, session):
    if not can_access_paid_session(request, session):
        return False
    assignment_attempt = getattr(session, "class_assignment_attempt", None)
    if assignment_attempt is None:
        return True
    return bool(
        request.user.is_authenticated
        and assignment_attempt.membership.student_id == request.user.pk
        and session.user_id == request.user.pk
    )
