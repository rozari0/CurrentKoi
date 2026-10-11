from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ConnectionSession, Device

THRESHOLD = timedelta(seconds=90)


class DeviceService:
    @staticmethod
    def get_device_by_key(key: str) -> Device | None:
        """
        Retrieve a device by its unique key.

        Args:
            key (str): The unique key of the device.

        Returns:
            Device | None: The device instance if found, otherwise None.
        """
        try:
            return Device.objects.get(key=key)
        except Device.DoesNotExist:
            return None

    @staticmethod
    def get_user_devices(user) -> list[Device]:
        """Return all devices owned by the given user, newest first."""
        return list(Device.objects.filter(user=user).order_by("-created_at"))

    @staticmethod
    def create_device(user, name: str) -> Device:
        """Create a device owned by the given user."""
        return Device.objects.create(user=user, name=name)

    @staticmethod
    def delete_device(device: Device) -> None:
        """Delete the given device and its connection sessions."""
        device.delete()

    @staticmethod
    @transaction.atomic
    def update_device_ping(device: Device) -> ConnectionSession:
        """
        Update the last ping time of a device and manage its connection session.

        Args:
            device (Device): The device instance to update.
        """
        now = timezone.now()
        local_now = timezone.localtime(now)
        device.last_ping = now
        device.save(update_fields=["last_ping"])

        active_session: ConnectionSession | None = (
            ConnectionSession.objects.filter(
                device=device,
                start_time__date=local_now.date(),
                end_time__gte=now - THRESHOLD,
            )
            .order_by("-end_time")
            .first()
        )

        if active_session:
            active_session.end_time = now
            active_session.save(update_fields=["end_time"])
            return active_session
        return ConnectionSession.objects.create(
            device=device, start_time=now, end_time=now
        )
