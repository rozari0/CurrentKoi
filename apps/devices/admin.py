from django.contrib import admin

from .models import ConnectionSession, Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "is_online", "created_at", "last_ping")
    search_fields = ("name", "user__username", "key")
    list_filter = ("created_at", "last_ping")


@admin.register(ConnectionSession)
class ConnectionSessionAdmin(admin.ModelAdmin):
    list_display = ("device", "start_time", "end_time", "duration")
    search_fields = ("device__name", "device__user__username")
    list_filter = ("start_time", "end_time")
