from django.contrib.auth.models import AbstractUser
from django.db import models
from django_lifecycle import BEFORE_CREATE, LifecycleModel, hook


class User(AbstractUser):
    pass


class APIKey(LifecycleModel):
    def __str__(self):
        return f"API Key for {self.user.username} - {self.id}"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @hook(BEFORE_CREATE)
    def generate_key(self):
        import secrets

        self.key = "sk_live_" + secrets.token_urlsafe(32)
