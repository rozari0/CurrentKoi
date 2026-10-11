from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from .api import api

urlpatterns = [
    path("", include("apps.devices.urls")),
    path("api/v1/", api.urls),
    path(
        "accounts/profile/",
        RedirectView.as_view(pattern_name="dashboard"),
        name="profile",
    ),
    path("accounts/", include("allauth.urls")),
]

if settings.KEEP_ADMIN_SITE:
    urlpatterns.append(path(f"{settings.ADMIN_SITE_PATH}", admin.site.urls))
