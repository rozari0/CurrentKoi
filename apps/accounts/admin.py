from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import APIKey, User

admin.site.register(User, BaseUserAdmin)


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "created_at")
    search_fields = ("user__username", "key")
    list_filter = ("created_at",)
    readonly_fields = ("key",)
