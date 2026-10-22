from django.urls import path
from . import views

app_name = "practice"

urlpatterns = [
    path("setup/", views.practice_setup, name="setup"),
    path("session/<int:session_id>/", views.session_view, name="session_view"),
    path("session/<int:session_id>/cbt/", views.session_view, name="cbt_exam"),
    path("session/<int:session_id>/time-sync/", views.time_sync, name="time_sync"),
    path("session/<int:session_id>/submit/<int:response_id>/", views.submit_answer, name="submit_answer"),
    path("session/<int:session_id>/finish/", views.finish_session, name="finish_session"),
    path("session/<int:session_id>/results/", views.session_results, name="session_results"),
]
