from __future__ import annotations

import functools
import itertools

from collections.abc import Iterator

import lxml  # nosec

from django import forms

from radiofeed.feedparser.xpath_parser import XPathParser
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.models import User


class UserPreferencesForm(forms.ModelForm):
    """Form for user settings."""

    class Meta:
        model = User

        fields = ("send_email_notifications",)

        labels = {
            "send_email_notifications": "Send email notifications",
        }

        help_texts = {
            "send_email_notifications": "I'd like to receive notications of new content and recommendations."
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

        Only feeds that already exist in the database will be included.

        Returns:
            number of new subscribed feeds
        """
        return len(
            Subscription.objects.bulk_create(
                [
                    Subscription(podcast=podcast, subscriber=user)
                    for podcast in itertools.islice(
                        Podcast.objects.filter(rss__in=set(self._parse_opml()))
                        .exclude(subscriptions__subscriber=user)
                        .distinct(),
                        limit,
                    )
                ],
                ignore_conflicts=True,
            )
        )

    def _parse_opml(self) -> Iterator[str]:
        self.cleaned_data["opml"].seek(0)

        parser = _xpath_parser()

        try:
            for element in parser.iterparse(
                self.cleaned_data["opml"].read(), "opml", "body"
            ):
                try:
                    yield from parser.iter(element, "//outline//@xmlUrl")
                finally:
                    element.clear()
        except lxml.etree.XMLSyntaxError:
            return


@functools.cache
def _xpath_parser() -> XPathParser:
    return XPathParser()
