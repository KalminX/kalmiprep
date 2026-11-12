"""Access policy for practice sessions purchased through teacher tests."""


def can_access_practice_session(request, session):
    purchase = getattr(session, "test_purchase", None)
    if purchase is None:
        return True
    if purchase.status != purchase.Status.PAID:
        return False
    if purchase.buyer_id and request.user.is_authenticated and request.user.id == purchase.buyer_id:
        return True
    return str(purchase.pk) in request.session.get("paid_test_purchases", [])
