from ninja_extra import api_controller, http_post, permissions

from .services import DeviceService
from .throttle import DeviceRateThrottle


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
