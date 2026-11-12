from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import ClassAssignment
from .realtime import assignment_group_name
from .results import teacher_assignment_snapshot


class AssignmentResultsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        assignment_id = self.scope["url_route"]["kwargs"]["assignment_id"]
        if not await self.user_owns_assignment(user.pk, assignment_id):
            await self.close(code=4403)
            return
        self.assignment_id = str(assignment_id)
        self.group_name = assignment_group_name(self.assignment_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_results()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def assignment_updated(self, event):
        await self.send_results()

    async def send_results(self):
        rows = await database_sync_to_async(teacher_assignment_snapshot)(self.assignment_id)
        if rows is not None:
            await self.send_json({"type": "results.updated", "rows": rows})

    @database_sync_to_async
    def user_owns_assignment(self, user_id, assignment_id):
        return ClassAssignment.objects.filter(
            pk=assignment_id,
            classroom__teacher__user_id=user_id,
            classroom__teacher__status="ACTIVE",
        ).exists()
