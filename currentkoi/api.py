from ninja_extra import NinjaExtraAPI

from apps.accounts.auth import AuthBearer
from apps.accounts.views import APIController
from apps.devices.views import DeviceController

api = NinjaExtraAPI(
    title="Current KOI API",
    description="API for Current KOI",
    version="1.0.0",
    auth=AuthBearer(),
)


api.register_controllers(APIController, DeviceController)
