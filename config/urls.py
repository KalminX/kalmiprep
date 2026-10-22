from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("curriculum/", include("curriculum.urls")),
    path("questions/", include("questions.urls")),
    path("practice/", include("practice.urls")),
    path("progress/", include("progress.urls")),
    path("accounts/", include("accounts.urls")),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
