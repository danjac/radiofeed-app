from typing import ClassVar

from django import forms

from radiofeed.podcasts.models import Podcast


class PodcastForm(forms.ModelForm):
    """Form to add a new podcast feed."""

    class Meta:
        model = Podcast
        fields: ClassVar[list] = ["rss"]
        labels: ClassVar[dict] = {"rss": "RSS Feed URL"}
        error_messages: ClassVar[dict] = {
            "rss": {"unique": "This podcast is not available"}
        }
