from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from jcasts.users.forms import UserChangeForm, UserCreationForm

User = get_user_model()


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
