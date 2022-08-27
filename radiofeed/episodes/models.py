from __future__ import annotations

import mimetypes
import pathlib

from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.templatetags.static import static
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext as _
from fast_update.query import FastUpdateManager
from model_utils.models import TimeStampedModel

from radiofeed.cleaners import strip_html
from radiofeed.db import FastCountMixin, SearchMixin
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


class EpisodeQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    """QuerySet for Episode model."""

    def with_current_time(self, user: User | AnonymousUser) -> models.QuerySet[Episode]:
        """Adds `current_time`, `remaining` and `listened` annotations.

        Both will be None if user is anonymous or there is no listening history.
        """
        if user.is_anonymous:
            return self.annotate(
                current_time=models.Value(0, output_field=models.IntegerField()),
                listened=models.Value(None, output_field=models.DateTimeField()),
            )

        logs = user.audio_logs.filter(episode=models.OuterRef("pk"))

        return self.annotate(
            current_time=models.Subquery(logs.values("current_time")),
            listened=models.Subquery(logs.values("listened")),
        )


class Episode(models.Model):
    """Individual podcast episode."""

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="episodes",
        verbose_name=_("Podcast"),
    )

    guid: str = models.TextField(verbose_name=_("RSS Feed GUID"))

    pub_date: datetime = models.DateTimeField(verbose_name=_("Release Date"))

    title: str = models.TextField(blank=True, verbose_name=_("Episode Title"))
    description: str = models.TextField(
        blank=True, verbose_name=_("Episode Description")
    )
    keywords: str = models.TextField(blank=True, verbose_name=_("Episode Keywords"))

    link: str | None = models.URLField(
        max_length=2083, null=True, blank=True, verbose_name=_("Episode Website Page")
    )

    episode_type: str = models.CharField(
        max_length=30, default="full", verbose_name=_("Episode Type")
    )
    episode: int | None = models.IntegerField(
        null=True, blank=True, verbose_name=_("Season Episode Number")
    )
    season: int | None = models.IntegerField(
        null=True, blank=True, verbose_name=_("Season")
    )

    cover_url: str | None = models.URLField(
        max_length=2083, null=True, blank=True, verbose_name=_("Cover Image")
    )

    media_url: str = models.URLField(
        max_length=2083, verbose_name=_("Audio URL Source")
    )
    media_type: str = models.CharField(max_length=60, verbose_name=_("Audio MIME Type"))

    length: int | None = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Duration (Seconds)")
    )
    duration: str = models.CharField(
        max_length=30, blank=True, verbose_name=_("Duration (Text)")
    )

    explicit: bool = models.BooleanField(
        default=False, verbose_name=_("Contains Explicit or Adult Content")
    )

    search_vector: str | None = SearchVectorField(
        null=True, editable=False, verbose_name=_("PostgreSQL Search Vector")
    )

    objects: models.Manager["Episode"] = EpisodeQuerySet.as_manager()
    fast_update_objects: models.Manager = FastUpdateManager()

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

    def is_bookmarked(self, user: User | AnonymousUser) -> bool:
        """Check if episode has been bookmarked by this user."""
        if user.is_anonymous:
            return False
        return Bookmark.objects.filter(user=user, episode=self).exists()

    @cached_property
    def cleaned_title(self) -> str:
        """Strips HTML from title field."""
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        """Strips HTML from description field."""
        return strip_html(self.description)

    @cached_property
    def duration_in_seconds(self) -> int:
        """Returns total number of seconds given string in [h:][m:]s format."""
        if not self.duration:
            return 0

        try:
            return sum(
                (int(part) * multiplier)
                for (part, multiplier) in zip(
                    reversed(self.duration.split(":")[:3]), (1, 60, 3600)
                )
            )
        except ValueError:
            return 0

    def is_explicit(self) -> bool:
        """Check if either this specific episode or the podcast is explicit."""
        return self.explicit or self.podcast.explicit

    def get_episode_metadata(self) -> str:
        """Returns the episode season/episode/type as a single string, e.g. "Episode 3 Season 4", "Trailer", etc."""
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
                    _("Episode {episode}").format(episode=self.episode)
                    if self.episode and not episode_type
                    else None,
                    _("Season {season}").format(season=self.season)
                    if self.season and not episode_type
                    else None,
                )
                if info
            ]
        )

    def get_media_url_ext(self) -> str:
        """Returns the path extension of the media URL, e.g. "mpeg"."""
        return pathlib.Path(self.media_url).suffix[1:]

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
        return f"player-actions-{self.id}"

    def get_bookmark_target(self) -> str:
        """Add/remove bookmark button HTMX target."""
        return f"bookmark-actions-{self.id}"

    def get_history_target(self) -> str:
        """Listening history episode detail HTMX target."""
        return f"history-actions-{self.id}"


class BookmarkQuerySet(SearchMixin, models.QuerySet):
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
        verbose_name=_("User"),
    )

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="bookmarks",
        verbose_name=_("User"),
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


class AudioLogQuerySet(SearchMixin, models.QuerySet):
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
        verbose_name=_("User"),
        related_name="audio_logs",
    )
    episode: Episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        verbose_name=_("Episode"),
        related_name="audio_logs",
    )

    listened: datetime = models.DateTimeField(verbose_name=_("Last Listened At"))
    current_time: int = models.IntegerField(
        default=0, verbose_name=_("Timestamp Mark (Seconds)")
    )

    objects: models.Manager["AudioLog"] = AudioLogQuerySet.as_manager()

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
