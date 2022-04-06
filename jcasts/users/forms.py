from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from jcasts.users.models import User


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields: tuple[str, ...] = ("send_email_notifications",)
        help_texts: dict[str, str] = {
            "send_email_notifications": "I'd like to receive notications of new content and recommendations.",
        }


class UserDeleteForm(forms.Form):

    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    def __init__(self, user: User, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self) -> str:
        password = self.data["password"]
        if not self.user.check_password(password):
            raise ValidationError("Password is not correct")
        return password
