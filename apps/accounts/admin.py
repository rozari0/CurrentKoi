from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.devices.models import Device

from .models import User

admin.site.register(User, BaseUserAdmin)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "created_at")
    search_fields = ("user__username", "key")
    list_filter = ("created_at",)
    readonly_fields = ("key",)
