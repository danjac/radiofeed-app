from django import forms
from django.db.models import Exists, OuterRef, Q

from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.models import User


class PrivateFeedForm(forms.Form):
    """Form to add a private feed."""

    rss = forms.URLField(
        max_length=300,
        label="Add Private Feed",
        help_text="RSS feed for podcast",
    )

    def clean_rss(self) -> str:
        """Validates RSS."""
        value = self.cleaned_data["rss"]

        if (
            Podcast.objects.annotate(
                has_subscriptions=Exists(
                    Subscription.objects.filter(podcast=OuterRef("pk"))
                ),
            )
            .filter(Q(Q(has_subscriptions=True) | Q(private=False)), rss=value)
            .exists()
        ):
            raise forms.ValidationError("This feed is not available")

        return value

    def save(self, user: User) -> tuple[Podcast, bool]:
        """Adds new podcast.

        Returns podcast instance and boolean to indicate podcast is new.
        """
        podcast, is_new = Podcast.objects.get_or_create(
            rss=self.cleaned_data["rss"],
            defaults={"private": True},
        )
        is_new = is_new or podcast.pub_date is None
        Subscription.objects.create(subscriber=user, podcast=podcast)
        return podcast, is_new
