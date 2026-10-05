from ninja_extra import api_controller, http_get

from apps.accounts.auth import AuthBearer


@api_controller(tags=["API Keys"])
class APIController:
    @http_get("/check", auth=[AuthBearer()])
    def checkapi(self, request) -> bool:
        """Check if Bearer Token is Valid or Not"""
        return not bool(request.user.is_anonymous)
