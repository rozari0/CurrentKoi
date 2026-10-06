from ninja_extra import api_controller, http_get

from apps.accounts.auth import AuthBearer


@api_controller(tags=["API Keys"])
class APIController:
    @http_get("/check")
    def checkapi(self, request):
        """Check if Bearer Token is Valid or Not"""
        return {
            "message": "Bearer Token is Valid",
            "user": request.user.username,
        }
