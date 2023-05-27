from django import forms

from radiofeed.podcasts.models import Podcast


class PrivateFeedForm(forms.Form):
    """Form to add a private feed."""

    rss = forms.URLField(max_length=300, label="Feed RSS")

    def clean_rss(self):
        """Validates RSS."""
        value = self.cleaned_data["rss"]

        if Podcast.objects.filter(rss=value, private=False).exists():
            raise forms.ValidationError("This is not a private feed")

        return value

    def save(self) -> Podcast:
        """Adds new podcast."""
        podcast, _ = Podcast.objects.get_or_create(
            rss=self.cleaned_data["rss"],
            defaults={"private": True},
        )
        return podcast
