from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import docs_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("docs/", docs_view, name="docs"),
    path("", include("core.urls")),
    path("curriculum/", include("curriculum.urls")),
    path("questions/", include("questions.urls")),
    path("practice/", include("practice.urls")),
    path("progress/", include("progress.urls")),
    path("accounts/", include("accounts.urls")),
    path("monetization/", include("monetization.urls")),
    path("classrooms/", include("classrooms.urls")),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
