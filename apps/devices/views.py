from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView
from ninja_extra import api_controller, http_post, permissions

from .forms import DeviceForm
from .models import THRESHOLD_SECONDS, ConnectionSession, Device
from .services import DeviceService
from .throttle import DeviceRateThrottle

DAILY_WINDOW_DAYS = 14
TIMELINE_SESSIONS = 15


def _session_seconds(session: ConnectionSession) -> float:
    end = session.end_time or timezone.now()
    return max((end - session.start_time).total_seconds(), 0.0)


def _online_seconds(sessions, start, end) -> float:
    """Total online time of the sessions overlapping the [start, end] window."""
    total = 0.0
    for session in sessions:
        session_end = session.end_time or end
        overlap = (
            min(session_end, end) - max(session.start_time, start)
        ).total_seconds()
        if overlap > 0:
            total += overlap
    return total


def _timeline_label(session: ConnectionSession) -> str:
    """Readable start → end label for a session, marking ongoing ones."""
    start = timezone.localtime(session.start_time)
    start_str = start.strftime("%b %d, %H:%M")
    if session.end_time is None:
        return f"{start_str} → ongoing"
    if (timezone.now() - session.end_time).total_seconds() < THRESHOLD_SECONDS:
        return f"{start_str} → ongoing"
    end = timezone.localtime(session.end_time)
    end_str = (
        end.strftime("%H:%M")
        if end.date() == start.date()
        else end.strftime("%b %d, %H:%M")
    )
    return f"{start_str} → {end_str}"


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
        start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        first_day = today - timedelta(days=DAILY_WINDOW_DAYS - 1)
        window_start = start_of_today - timedelta(days=DAILY_WINDOW_DAYS - 1)

        sessions = list(
            ConnectionSession.objects.filter(device=device)
            .filter(Q(end_time__gte=window_start) | Q(end_time__isnull=True))
            .order_by("start_time")
        )

        days = [
            first_day + timedelta(days=offset) for offset in range(DAILY_WINDOW_DAYS)
        ]
        daily_counts = dict.fromkeys(days, 0)
        daily_online_seconds = dict.fromkeys(days, 0.0)
        daily_offline_seconds = dict.fromkeys(days, 0.0)

        for session in sessions:
            day = timezone.localtime(session.start_time).date()
            if day in daily_counts:
                daily_counts[day] += 1

        for day in days:
            day_start = start_of_today - timedelta(days=(today - day).days)
            monitored_start = max(day_start, device.created_at)
            monitored_end = min(day_start + timedelta(days=1), local_now)
            monitored_seconds = (monitored_end - monitored_start).total_seconds()
            if monitored_seconds <= 0:
                continue
            online_seconds = _online_seconds(sessions, monitored_start, monitored_end)
            daily_online_seconds[day] = online_seconds
            daily_offline_seconds[day] = max(monitored_seconds - online_seconds, 0.0)

        today_seconds = daily_online_seconds[today]
        today_offline_seconds = daily_offline_seconds[today]

        timeline = sessions[-TIMELINE_SESSIONS:]

        context["daily_labels"] = [day.strftime("%b %d") for day in days]
        context["daily_hours"] = [
            round(daily_online_seconds[day] / 3600, 2) for day in days
        ]
        context["daily_offline_hours"] = [
            round(daily_offline_seconds[day] / 3600, 2) for day in days
        ]

        context["timeline_labels"] = [_timeline_label(session) for session in timeline]
        context["timeline_minutes"] = [
            round(_session_seconds(session) / 60, 1) for session in timeline
        ]

        context["today_uptime_hours"] = round(today_seconds / 3600, 2)
        context["today_uptime_minutes"] = int(
            (context["today_uptime_hours"] - int(context["today_uptime_hours"])) * 60
        )
        context["today_uptime_hours"] = int(context["today_uptime_hours"])
        context["today_offline_hours"] = round(today_offline_seconds / 3600, 2)
        context["today_outage_count"] = max(daily_counts.get(today, 0) - 1, 0)
        context["total_session_count"] = ConnectionSession.objects.filter(
            device=device
        ).count()

        context["chart_data"] = {
            "daily": {
                "labels": context["daily_labels"],
                "hours": context["daily_hours"],
                "offlineHours": context["daily_offline_hours"],
            },
            "timeline": {
                "labels": context["timeline_labels"],
                "minutes": context["timeline_minutes"],
            },
            "today": {
                "uptimeHours": context["today_uptime_hours"],
                "uptimeMinutes": context["today_uptime_minutes"],
                "offlineHours": context["today_offline_hours"],
            },
        }
        return context


class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return self._render(request)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        if action == "add":
            return self._add(request)
        if action == "delete":
            return self._delete(request)

        return self._render(request)

    def _render(self, request, form=None):
        context = {
            "form": form or DeviceForm(),
            "devices": DeviceService.get_user_devices(request.user),
        }
        return render(request, "devices/dashboard.html", context)

    def _add(self, request):
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = DeviceService.create_device(
                request.user, form.cleaned_data["name"]
            )
            messages.success(request, f"Added device “{device.name}”.")
            return redirect("dashboard")
        return self._render(request, form=form)

    def _delete(self, request):
        device = get_object_or_404(
            Device, pk=request.POST.get("device_id"), user=request.user
        )
        name = device.name
        DeviceService.delete_device(device)
        messages.success(request, f"Removed device “{name}”.")
        return redirect("dashboard")


class FlashView(View):
    def get(self, request):
        return redirect("https://current-koi-tools.vercel.app/")
