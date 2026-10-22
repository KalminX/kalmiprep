from django.urls import path
from . import views

app_name = "questions"

urlpatterns = [
    path("", views.question_list, name="question_list"),
    path("all/", views.question_list, name="list"),
    path("<int:pk>/", views.study_question, name="study_question"),
    path("<int:pk>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
]
