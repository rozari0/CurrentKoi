from ninja_extra.throttling import UserRateThrottle


class DeviceRateThrottle(UserRateThrottle):
    """Throttle for device ping requests."""

    rate = "5/min"
    scope = "minutes"
