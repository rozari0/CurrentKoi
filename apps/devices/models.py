import secrets
from uuid import uuid7

from django.db import models
from django.utils import timezone
from django_lifecycle import BEFORE_CREATE, LifecycleModel, hook

from apps.accounts.models import User


class Device(LifecycleModel):
    class Meta:
        db_table = "devices"

    def __str__(self):
        return f"Device: {self.name} for {self.user.username} - {self.id}"

    @property
    def is_online(self):
        if self.last_ping:
            return (
                self.last_ping - self.created_at
            ).total_seconds() < 90  # 30 seconds threshold for online status
        return False

    @hook(BEFORE_CREATE)
    def generate_key(self):
        self.key = f"{self.user.id}_" + secrets.token_urlsafe(10).replace(
            "-", ""
        ).replace("_", "")

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_ping = models.DateTimeField(null=True, blank=True)


class ConnectionSession(LifecycleModel):
    class Meta:
        db_table = "connection_sessions"

    @property
    def duration(self):
        """Returns the length of time the device was continuously online."""
        return self.end_time - self.start_time

    def __str__(self):
        return f"{self.device.name}: {self.start_time} to {self.end_time}"

    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    start_time = models.DateTimeField(db_index=True, default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True, db_index=True)
