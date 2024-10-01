from django import forms

from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.models import User


class PrivateFeedForm(forms.Form):
    """Form to add a private feed."""

    rss = forms.URLField(
        max_length=300,
        label="Add Private Feed",
        help_text="RSS feed for podcast",
    )

    def __init__(self, *args, user: User, **kwargs) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_rss(self) -> str:
        """Validates RSS."""
        value = self.cleaned_data["rss"]

        if Podcast.objects.filter(rss=value, private=False).exists():
            raise forms.ValidationError("This is not a private feed")

        if (
            subscription := Subscription.objects.filter(podcast__rss=value)
            .select_related("subscriber")
            .first()
        ):
            message = (
                "You are already subscribed to this feed"
                if subscription.subscriber == self.user
                else "This feed is already subscribed by someone else"
            )
            raise forms.ValidationError(message)
        return value

    def save(self) -> tuple[Podcast, bool]:
        """Adds new podcast.

        Returns podcast instance and boolean to indicate podcast is new.
        """
        podcast, is_new = Podcast.objects.get_or_create(
            rss=self.cleaned_data["rss"],
            defaults={"private": True},
        )
        is_new = is_new or podcast.pub_date is None
        Subscription.objects.create(subscriber=self.user, podcast=podcast)
        return podcast, is_new
