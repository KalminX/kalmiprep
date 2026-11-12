from django.urls import path

from . import views

app_name = "classrooms"

urlpatterns = [
    path("", views.classroom_index, name="index"),
    path("classes/new/", views.create_class, name="create_class"),
    path("classes/<uuid:class_id>/", views.classroom_detail, name="detail"),
    path("assignments/new/", views.create_assignment, name="create_assignment"),
    path("assignments/<uuid:assignment_id>/", views.assignment_detail, name="assignment_detail"),
    path("assignments/<uuid:assignment_id>/start/", views.start_assignment, name="start_assignment"),
]
