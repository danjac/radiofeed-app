from typing import ClassVar

from django.contrib import admin
from django.contrib.auth import admin as auth_admin

from listenwave.users.models import User


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    """User model admin."""

    list_display: ClassVar[list[str]] = [
        "username",
        "email",
        "is_superuser",
        "date_joined",
        "last_login",
    ]
    search_fields: ClassVar[list[str]] = ["email", "username"]
    ordering: ClassVar[list[str]] = ["-date_joined", "-last_login"]
