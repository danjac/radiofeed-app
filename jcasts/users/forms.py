from __future__ import annotations

from captcha.fields import ReCaptchaField
from django import forms
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.http import HttpRequest

from jcasts.shared.typedefs import User


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields: tuple[str, ...] = (
            "autoplay",
            "send_recommendations_email",
        )
        help_texts: dict[str, str] = {
            "autoplay": "Automatically play the next episode in my Play Queue when the current playing episode ends",
            "send_recommendations_email": "Send me podcast recommendations every week",
        }


class RecaptchaSignupForm(forms.Form):
    captcha = ReCaptchaField()

    def signup(self, request: HttpRequest, user: User) -> None:
        """This function is required otherwise you will get an ImproperlyConfigured exception"""
        pass
