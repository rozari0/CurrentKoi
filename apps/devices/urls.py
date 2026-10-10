from django.urls import path

from .views import DeviceDetailView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("device/<slug:pk>/", DeviceDetailView.as_view(), name="device_detail"),
]
