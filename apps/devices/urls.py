from django.urls import path

from .views import DashboardView, DeviceDetailView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("device/<slug:pk>/", DeviceDetailView.as_view(), name="device_detail"),
]
