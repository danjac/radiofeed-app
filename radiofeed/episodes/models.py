from __future__ import annotations

import mimetypes
from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.templatetags.static import static
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from fast_update.query import FastUpdateQuerySet
from model_utils.models import TimeStampedModel

from radiofeed import cleaners
from radiofeed.fast_count import FastCountQuerySetMixin
from radiofeed.podcasts.models import Podcast
from radiofeed.search import SearchQuerySetMixin
from radiofeed.users.models import User


class EpisodeQuerySet(FastCountQuerySetMixin, SearchQuerySetMixin, FastUpdateQuerySet):
    """QuerySet for Episode model."""


class Episode(models.Model):
    """Individual podcast episode."""

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="episodes",
    )

    guid: str = models.TextField()

    pub_date: datetime = models.DateTimeField()

    title: str = models.TextField(blank=True)
    description: str = models.TextField(blank=True)
    keywords: str = models.TextField(blank=True)

    link: str | None = models.URLField(max_length=2083, null=True, blank=True)

    episode_type: str = models.CharField(max_length=30, default="full")
    episode: int | None = models.IntegerField(null=True, blank=True)
    season: int | None = models.IntegerField(null=True, blank=True)

    cover_url: str | None = models.URLField(max_length=2083, null=True, blank=True)

    media_url: str = models.URLField(max_length=2083)
    media_type: str = models.CharField(max_length=60)

    length: int | None = models.BigIntegerField(null=True, blank=True)
    duration: str = models.CharField(max_length=30, blank=True)

    explicit: bool = models.BooleanField(default=False)

    search_vector: str | None = SearchVectorField(null=True, editable=False)

    objects: models.Manager[Episode] = EpisodeQuerySet.as_manager()  # pyright: ignore

    # annotations

    current_time: datetime | None = None
    listened: datetime | None = None

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_podcast_guid",
                fields=["podcast", "guid"],
            )
        ]
        indexes = [
            models.Index(fields=["podcast", "pub_date"]),
            models.Index(fields=["podcast", "-pub_date"]),
            models.Index(fields=["podcast"]),
            models.Index(fields=["guid"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["-pub_date", "-id"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self) -> str:
        """Returns title or guid."""
        return self.title or self.guid

    def get_absolute_url(self) -> str:
        """URL of episode detail page."""
        return reverse("episodes:episode_detail", args=[self.pk, self.slug])

    def get_next_episode(self) -> Episode | None:
        """Returns the next episode in this podcast."""
        try:
            return self.get_next_by_pub_date(podcast=self.podcast)
        except self.DoesNotExist:
            return None

    def get_previous_episode(self) -> Episode | None:
        """Returns the previous episode in this podcast."""
        try:
            return self.get_previous_by_pub_date(podcast=self.podcast)
        except self.DoesNotExist:
            return None

    @property
    def slug(self) -> str:
        """Returns slugified title, if any."""
        return slugify(self.title, allow_unicode=False) or "no-title"

    def get_link(self) -> str | None:
        """Returns link to episode web page or podcast site if former not provided."""
        return self.link or self.podcast.link

    def get_file_size(self) -> str | None:
        """Returns human readable file size e.g. 30MB.

        If length is zero or none returns None.
        """
        return filesizeformat(self.length) if self.length else None

    def get_cover_url(self) -> str | None:
        """Returns cover image URL or podcast cover image if former not provided."""
        return self.cover_url or self.podcast.cover_url

    @cached_property
    def cleaned_title(self) -> str:
        """Strips HTML from title field."""
        return cleaners.strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        """Strips HTML from description field."""
        return cleaners.strip_html(self.description)

    @cached_property
    def duration_in_seconds(self) -> int:
        """Returns total number of seconds given string in [h:][m:]s format."""
        if not self.duration:
            return 0

        try:
            return sum(
                (int(part) * multiplier)
                for (part, multiplier) in zip(
                    reversed(self.duration.split(":")[:3]),
                    (1, 60, 3600),
                    strict=False,
                )
            )
        except ValueError:
            return 0

    def is_explicit(self) -> bool:
        """Check if either this specific episode or the podcast is explicit."""
        return self.explicit or self.podcast.explicit

    def get_episode_metadata(self) -> str:
        """Returns the episode season/episode/type as a single string, e.g.
        "Episode 3 Season 4", "Trailer", etc."""
        episode_type = (
            self.episode_type.capitalize()
            if self.episode_type and self.episode_type.casefold() != "full"
            else None
        )

        return " ".join(
            [
                info
                for info in (
                    episode_type,
                    f"Episode {self.episode}"
                    if self.episode and not episode_type
                    else None,
                    f"Season {self.season}"
                    if self.season and not episode_type
                    else None,
                )
                if info
            ]
        )

    def get_media_metadata(self) -> dict:
        """Returns media session metadata for integration with client device.

        For more details:

            https://developers.google.com/web/updates/2017/02/media-session
        """
        cover_url = self.podcast.cover_url or static("img/podcast-icon.png")
        cover_url_type, _ = mimetypes.guess_type(urlparse(cover_url).path)

        return {
            "title": self.cleaned_title,
            "album": self.podcast.cleaned_title,
            "artist": self.podcast.owner,
            "artwork": [
                {
                    "src": cover_url,
                    "sizes": f"{size}x{size}",
                    "type": cover_url_type,
                }
                for size in [96, 128, 192, 256, 384, 512]
            ],
        }

    def get_player_target(self) -> str:
        """Play button HTMX target."""
        return f"player-actions-{self.pk}"

    def get_bookmark_target(self) -> str:
        """Add/remove bookmark button HTMX target."""
        return f"bookmark-actions-{self.pk}"

    def get_history_target(self) -> str:
        """Listening history episode detail HTMX target."""
        return f"episode-timestamps-{self.pk}"


class BookmarkQuerySet(SearchQuerySetMixin, models.QuerySet):
    """QuerySet for Bookmark model."""

    search_vectors = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


class Bookmark(TimeStampedModel):
    """Bookmarked episodes."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    objects = BookmarkQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_episode",
                fields=["user", "episode"],
            )
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]


class AudioLogQuerySet(SearchQuerySetMixin, models.QuerySet):
    """QuerySet for AudioLog."""

    search_vectors = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


class AudioLog(TimeStampedModel):
    """Record of user listening history."""

    user: User = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audio_logs",
    )
    episode: Episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="audio_logs",
    )

    listened: datetime = models.DateTimeField()
    current_time: int = models.IntegerField(default=0)

    objects: models.Manager[AudioLog] = AudioLogQuerySet.as_manager()  # pyright: ignore

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_episode",
                fields=["user", "episode"],
            ),
        ]
        indexes = [
            models.Index(fields=["-listened"]),
            models.Index(fields=["listened"]),
        ]
