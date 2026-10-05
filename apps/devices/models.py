import secrets
from uuid import uuid7

from django.db import models
from django_lifecycle import BEFORE_CREATE, LifecycleModel, hook

from apps.accounts.models import User


class Device(LifecycleModel):
    class Meta:
        db_table = "devices"

    def __str__(self):
        return f"Device: {self.name} for {self.user.username} - {self.id}"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @hook(BEFORE_CREATE)
    def generate_key(self):
        self.key = f"{self.user.id}_" + secrets.token_urlsafe(10).replace(
            "-", ""
        ).replace("_", "")
