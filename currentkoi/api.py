from ninja_extra import NinjaExtraAPI

from apps.accounts.api import APIController

api = NinjaExtraAPI(
    title="Current KOI API",
    description="API for Current KOI",
    version="1.0.0",
)


api.register_controllers(APIController)
