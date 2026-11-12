from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("docs/", views.docs_view, name="docs"),
    path("api/telemetry/error-beacon/", views.telemetry_beacon_view, name="error_beacon"),
]
