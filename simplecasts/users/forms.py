from typing import ClassVar

from django import forms

from simplecasts.users.models import User


class UserPreferencesForm(forms.ModelForm):
    """Form for user settings."""

    class Meta:
        model = User

        fields = ("send_email_notifications",)

        labels: ClassVar[dict[str, str]] = {
            "send_email_notifications": "Send email notifications",
        }

        help_texts: ClassVar[dict[str, str]] = {
            "send_email_notifications": "I'd like to receive notifications of new content to my primary email address."
        }


class AccountDeletionConfirmationForm(forms.Form):
    """Form for deleting user account."""

    required_value: str = "delete me"

    confirm_delete = forms.CharField(
        required=True,
        label=f'To confirm deletion, type "{required_value}"',
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def clean_confirm_delete(self) -> str:
        """Validates confirmation input."""
        value = self.cleaned_data["confirm_delete"]
        if value != self.required_value:
            raise forms.ValidationError(
                f'You must type "{self.required_value}" to confirm account deletion.'
            )
        return value


class OpmlUploadForm(forms.Form):
    """Form for uploading OPML into user collection."""

    opml = forms.FileField(
        label="Select OPML file",
        widget=forms.FileInput(
            attrs={
                "accept": ".opml,.xml,application/xml,text/x-opml,text/xml",
            }
        ),
    )
