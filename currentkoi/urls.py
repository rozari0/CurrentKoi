from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .api import api

urlpatterns = [
    path("", include("apps.devices.urls")),
    path("api/v1/", api.urls),
    path("accounts/", include("allauth.urls")),
]

if settings.KEEP_ADMIN_SITE:
    urlpatterns.append(path(f"{settings.ADMIN_SITE_PATH}", admin.site.urls))
