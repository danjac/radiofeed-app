from typing import ClassVar

from django import forms

from radiofeed.feedparser.opml_parser import parse_opml
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.models import User


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


class DeleteAccountForm(forms.Form):
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

    def subscribe_to_feeds(self, user: User, limit: int = 360) -> list[Subscription]:
        """Subscribes user to feeds in uploaded OPML.

        Only active public feeds that already exist in the database will be included.

        Returns:
            number of subscribed feeds
        """
        self.cleaned_data["opml"].seek(0)

        if urls := set(parse_opml(self.cleaned_data["opml"].read())) - set(
            Subscription.objects.filter(subscriber=user)
            .select_related("podcast")
            .values_list("podcast__rss", flat=True)
        ):
            podcasts = Podcast.objects.filter(
                active=True,
                private=False,
                rss__in=urls,
            )[:limit]

            return Subscription.objects.bulk_create(
                [
                    Subscription(podcast=podcast, subscriber=user)
                    for podcast in podcasts.iterator()
                ],
                ignore_conflicts=True,
            )

        return []
