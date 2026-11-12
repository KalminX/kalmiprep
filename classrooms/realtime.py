import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def assignment_group_name(assignment_id):
    return f"class_assignment_{str(assignment_id).replace('-', '')}"


def broadcast_assignment_update(assignment_id):
    def send_update():
        try:
            layer = get_channel_layer()
            if layer is None:
                return
            async_to_sync(layer.group_send)(
                assignment_group_name(assignment_id),
                {"type": "assignment.updated"},
            )
        except Exception:
            logger.exception("Unable to broadcast classroom assignment update")

    transaction.on_commit(send_update)


def broadcast_class_update(classroom_id):
    from .models import ClassAssignment

    assignment_ids = list(ClassAssignment.objects.filter(classroom_id=classroom_id).values_list("pk", flat=True))
    for assignment_id in assignment_ids:
        broadcast_assignment_update(assignment_id)
