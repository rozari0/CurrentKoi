from datetime import timedelta

from django.utils import timezone
from django.views.generic import DetailView, TemplateView
from ninja_extra import api_controller, http_post, permissions

from .models import ConnectionSession, Device
from .services import DeviceService
from .throttle import DeviceRateThrottle

DAILY_WINDOW_DAYS = 14
TIMELINE_SESSIONS = 15


def _session_seconds(session: ConnectionSession) -> float:
    end = session.end_time or timezone.now()
    return max((end - session.start_time).total_seconds(), 0.0)


@api_controller(
    "/devices", tags=["Devices"], permissions=[permissions.IsAuthenticated()]
)
class DeviceController:
    def __init__(self, device_service: DeviceService):
        self.device_service = device_service

    @http_post("/ping", throttle=DeviceRateThrottle())
    def ping_device(self, request):
        """
        Ping a device. Rates are limited to 5 requests per minute per device.
        The device is identified by the token provided in the request header. If the token is valid, the device's session is updated and a response is returned with the session details.
        """
        token = request.token

        device = self.device_service.get_device_by_key(token)
        session = self.device_service.update_device_ping(device)

        return {
            "message": f"Updated session for {device.name}",
            "session_id": session.id,
            "start_time": session.start_time,
            "end_time": session.end_time,
        }


class HomeView(TemplateView):
    template_name = "home.html"


class DeviceDetailView(DetailView):
    model = Device
    template_name = "devices/device_detail.html"
    context_object_name = "device"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.object

        local_now = timezone.localtime()
        today = local_now.date()
        first_day = today - timedelta(days=DAILY_WINDOW_DAYS - 1)

        sessions = list(
            ConnectionSession.objects.filter(
                device=device,
                start_time__date__gte=first_day,
            ).order_by("start_time")
        )

        days = [
            first_day + timedelta(days=offset) for offset in range(DAILY_WINDOW_DAYS)
        ]
        daily_seconds = dict.fromkeys(days, 0.0)
        daily_counts = dict.fromkeys(days, 0)

        for session in sessions:
            day = timezone.localtime(session.start_time).date()
            if day in daily_seconds:
                daily_seconds[day] += _session_seconds(session)
                daily_counts[day] += 1

        today_seconds = daily_seconds.get(today, 0.0)
        start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed_seconds = (local_now - start_of_today).total_seconds()
        today_offline_seconds = max(elapsed_seconds - today_seconds, 0.0)

        timeline = sessions[-TIMELINE_SESSIONS:]

        context["daily_labels"] = [day.strftime("%b %d") for day in days]
        context["daily_hours"] = [round(daily_seconds[day] / 3600, 2) for day in days]
        context["daily_counts"] = [daily_counts[day] for day in days]

        context["timeline_labels"] = [
            timezone.localtime(session.start_time).strftime("%b %d, %H:%M")
            for session in timeline
        ]
        context["timeline_minutes"] = [
            round(_session_seconds(session) / 60, 1) for session in timeline
        ]

        context["today_uptime_hours"] = round(today_seconds / 3600, 2)
        context["today_offline_hours"] = round(today_offline_seconds / 3600, 2)
        context["today_session_count"] = daily_counts.get(today, 0)
        context["total_session_count"] = ConnectionSession.objects.filter(
            device=device
        ).count()

        context["chart_data"] = {
            "daily": {
                "labels": context["daily_labels"],
                "hours": context["daily_hours"],
                "counts": context["daily_counts"],
            },
            "timeline": {
                "labels": context["timeline_labels"],
                "minutes": context["timeline_minutes"],
            },
            "today": {
                "uptimeHours": context["today_uptime_hours"],
                "offlineHours": context["today_offline_hours"],
            },
        }
        return context
