from django.contrib.auth.models import AnonymousUser
from ninja.security import HttpBearer

from apps.devices.models import Device


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        request.token = token
        try:
            api = Device.objects.get(key=token)
            request.user = api.user
        except Device.DoesNotExist:
            request.user = AnonymousUser()

        return request.user
