from typing import ClassVar

from django import forms

from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.podcasts.opml import parse_opml
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
            "send_email_notifications": "I'd like to receive notications of new content and recommendations."
        }


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

        if urls := set(parse_opml(self.cleaned_data["opml"])) - set(
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
