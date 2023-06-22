from django import forms

from radiofeed.podcasts.models import Podcast, Subscription


class PrivateFeedForm(forms.Form):
    """Form to add a private feed."""

    rss = forms.URLField(max_length=300, label="Feed RSS")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_rss(self) -> str:
        """Validates RSS."""
        value = self.cleaned_data["rss"]

        if Subscription.objects.filter(
            subscriber=self.user, podcast__rss=value
        ).exists():
            msg = "You are already subscribed to this podcast"
            raise forms.ValidationError(msg)

        if Podcast.objects.filter(rss=value, private=False).exists():
            msg = "This is not a private feed"
            raise forms.ValidationError(msg)

        return value

    def save(self) -> Podcast:
        """Adds new podcast."""
        podcast, _ = Podcast.objects.get_or_create(
            rss=self.cleaned_data["rss"],
            defaults={"private": True},
        )
        Subscription.objects.create(subscriber=self.user, podcast=podcast)
        return podcast
