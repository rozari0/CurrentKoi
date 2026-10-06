from django.conf import settings
from django.contrib import admin
from django.urls import path

from .api import api

urlpatterns = [
    path("api/v1/", api.urls),
]

if settings.KEEP_ADMIN_SITE:
    urlpatterns.append(path(f"{settings.ADMIN_SITE_PATH}", admin.site.urls))
