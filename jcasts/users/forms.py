from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from jcasts.core.typedefs import User


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields: tuple[str, ...] = ("send_email_notifications",)
        help_texts: dict[str, str] = {
            "send_email_notifications": "I'd like to receive notications of new content and recommendations.",
        }
