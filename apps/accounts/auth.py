from ninja.security import HttpBearer

from apps.devices.models import Device


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            api = Device.objects.get(key=token)
            request.user = api.user
        except Device.DoesNotExist:
            request.user = None

        return request.user
