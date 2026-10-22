from django.urls import path
from progress import views

app_name = "progress"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("bookmarks/", views.bookmarks_list, name="bookmarks"),
    path("extractor-status/", views.extractor_status, name="extractor_status"),
]
