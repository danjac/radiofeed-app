from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from simplecasts.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User model admin."""

    fieldsets = (
        *tuple(BaseUserAdmin.fieldsets or ()),
        (
            "User preferences",
            {
                "fields": ("send_email_notifications",),
            },
        ),
    )
