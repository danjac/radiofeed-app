from __future__ import annotations

import itertools

from typing import Iterator

import lxml

from django import forms

from radiofeed.common.utils.xml import parse_xml, xpath_finder
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.models import User


class UserPreferencesForm(forms.ModelForm):
    """Form for user settings."""

    class Meta:
        model = User
        fields = ("send_email_notifications",)
        help_texts = {
            "send_email_notifications": "I'd like to receive notications of new content and recommendations.",
        }


class OpmlUploadForm(forms.Form):
    """Form for uploading OPML into user collection."""

    opml = forms.FileField(
        label="Select OPML file",
        widget=forms.FileInput(
            attrs={
                "accept": ",".join(
                    [
                        ".opml",
                        ".xml",
                        "application/xml",
                        "text/x-opml",
                        "text/xml",
                    ]
                )
            }
        ),
    )

    def subscribe_to_feeds(self, user: User, limit: int = 300) -> int:
        """Subscribes user to feeds in uploaded OPML.

        Returns:
            nt: number of new subscribed feeds
        """
        return len(
            Subscription.objects.bulk_create(
                [
                    Subscription(podcast=podcast, user=user)
                    for podcast in itertools.islice(
                        Podcast.objects.filter(rss__in=self._parse_opml())
                        .exclude(subscription__user=user)
                        .distinct(),
                        limit,
                    )
                ],
                ignore_conflicts=True,
            )
        )

    def _parse_opml(self) -> Iterator[str]:
        self.cleaned_data["opml"].seek(0)

        try:
            for element in parse_xml(self.cleaned_data["opml"].read(), "outline"):
                with xpath_finder(element) as finder:
                    if rss := finder.first("@xmlUrl"):
                        yield rss
        except lxml.etree.XMLSyntaxError:
            return
