from __future__ import annotations

from django import forms

from radiofeed.users.models import User


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields: tuple[str, ...] = ("send_email_notifications",)
        help_texts: dict[str, str] = {
            "send_email_notifications": "I'd like to receive notications of new content and recommendations.",
        }
