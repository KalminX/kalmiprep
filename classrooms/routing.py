from django.urls import path

from .consumers import AssignmentResultsConsumer

websocket_urlpatterns = [
    path(
        "ws/classrooms/assignments/<uuid:assignment_id>/",
        AssignmentResultsConsumer.as_asgi(),
        name="classroom_assignment_results_ws",
    ),
]
