from ninja_extra import api_controller, http_post

from .services import DeviceService


@api_controller("/devices", tags=["Devices"])
class DeviceController:
    def __init__(self, device_service: DeviceService):
        self.device_service = device_service

    @http_post("/ping")
    def ping_device(self, request):
        """
        Ping a device.
        """
        token = request.auth

        device = self.device_service.get_device_by_key(token)
        session = self.device_service.update_device_ping(device)

        return {
            "message": f"Updated session for {device.name}",
            "session_id": session.id,
            "start_time": session.start_time,
            "end_time": session.end_time,
        }
