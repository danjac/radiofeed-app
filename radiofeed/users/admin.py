from django.contrib import admin
from django.contrib.auth import admin as auth_admin

from radiofeed.users.models import User


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    """User model admin."""

    list_display = [
        "username",
        "email",
        "is_superuser",
        "date_joined",
        "last_login",
    ]
    search_fields = ["email", "username"]
    ordering = ["-date_joined", "-last_login"]
