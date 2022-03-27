from django.contrib import admin
from django.contrib.auth import admin as auth_admin

from jcasts.users.forms import UserChangeForm, UserCreationForm
from jcasts.users.models import User


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    fieldsets = (
        ("User", {"fields": ("send_recommendations_email",)}),
    ) + auth_admin.UserAdmin.fieldsets

    list_display = [
        "username",
        "email",
        "is_superuser",
        "date_joined",
        "last_login",
    ]
    search_fields = ["email", "username"]
    ordering = ["-date_joined", "-last_login"]
