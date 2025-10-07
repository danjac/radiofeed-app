from typing import ClassVar, Optional

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models.fields.tuple_lookups import (  # type: ignore[reportMissingTypeStubs]
    TupleGreaterThan,
    TupleLessThan,
)
from django.urls import reverse
from django.utils.functional import cached_property
from fast_update.query import FastUpdateQuerySet
from slugify import slugify

from radiofeed.fields import URLField
from radiofeed.html import strip_html
from radiofeed.podcasts.models import Season
from radiofeed.search import SearchQuerySetMixin
from radiofeed.users.models import User


class EpisodeQuerySet(SearchQuerySetMixin, FastUpdateQuerySet):
    """QuerySet for Episode model."""

    def subscribed(self, user: User) -> models.QuerySet["Episode"]:
        """Returns episodes belonging to episodes subscribed by user."""
        return self.filter(podcast__subscriptions__subscriber=user)


class Episode(models.Model):
    """Individual podcast episode."""

    class EpisodeType(models.TextChoices):
        FULL = "full", "Full episode"
        TRAILER = "trailer", "Trailer"
        BONUS = "bonus", "Bonus"

    podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="episodes",
    )

    guid = models.TextField()

    pub_date = models.DateTimeField()

    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)

    cover_url = URLField(blank=True)

    website = URLField(blank=True)

    episode_type = models.CharField(
        max_length=12,
        choices=EpisodeType.choices,
        default=EpisodeType.FULL,
    )

    episode = models.IntegerField(null=True, blank=True)
    season = models.IntegerField(null=True, blank=True)

    media_url = URLField()

    media_type = models.CharField(max_length=60)

    file_size = models.BigIntegerField(
        null=True, blank=True, verbose_name="File size in bytes"
    )
    duration = models.CharField(max_length=30, blank=True)

    explicit = models.BooleanField(default=False)

    search_vector = SearchVectorField(null=True, editable=False)

    objects: models.Manager["Episode"] = EpisodeQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_podcast_guid",
                fields=["podcast", "guid"],
            )
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["pub_date", "podcast", "id"]),
            models.Index(fields=["-pub_date", "podcast", "-id"]),
            models.Index(fields=["podcast", "-pub_date", "-id"]),
            models.Index(fields=["podcast", "season"]),
            models.Index(fields=["pub_date", "id"]),
            models.Index(fields=["-pub_date", "-id"]),
            models.Index(fields=["guid"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self) -> str:
        """Returns title or guid."""
        return self.title or self.guid

    def get_absolute_url(self) -> str:
        """Canonical episode URL."""
        return reverse(
            "episodes:episode_detail",
            kwargs={
                "episode_id": self.pk,
                "slug": self.slug,
            },
        )

    def get_cover_url(self) -> str:
        """Returns cover image URL or podcast cover image if former not provided."""
        return self.cover_url or self.podcast.cover_url

    def is_explicit(self) -> bool:
        """Check if either this specific episode or the podcast is explicit."""
        return self.explicit or self.podcast.explicit

    def get_season(self) -> Season | None:
        """Returns season object if episode has a season."""
        return self.podcast.get_season(season=self.season) if self.season else None

    @cached_property
    def next_episode(self) -> Optional["Episode"]:
        """Returns the next episode in this podcast."""
        return (
            self._get_other_episodes_in_podcast()
            .filter(
                TupleGreaterThan(
                    (models.F("pub_date"), models.F("id")),
                    (models.Value(self.pub_date), models.Value(self.pk)),
                ),
            )
            .order_by(
                "pub_date",
                "id",
            )
            .first()
        )

    @cached_property
    def previous_episode(self) -> Optional["Episode"]:
        """Returns the previous episode in this podcast."""
        return (
            self._get_other_episodes_in_podcast()
            .filter(
                TupleLessThan(
                    (models.F("pub_date"), models.F("id")),
                    (models.Value(self.pub_date), models.Value(self.pk)),
                )
            )
            .order_by(
                "-pub_date",
                "-id",
            )
            .first()
        )

    @cached_property
    def slug(self) -> str:
        """Returns slugified title, if any."""
        return slugify(self.title) or "episode"

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
                    reversed(self.duration.split(":")[:3]),
                    (1, 60, 3600),
                    strict=False,
                )
            )
        except ValueError:
            return 0

    def _get_other_episodes_in_podcast(self) -> models.QuerySet["Episode"]:
        return self._meta.default_manager.filter(  # type: ignore[reportOptionalMemberAccess]
            podcast=self.podcast,
        ).exclude(pk=self.pk)


class BookmarkQuerySet(SearchQuerySetMixin, models.QuerySet):
    """QuerySet for Bookmark model."""

    search_vectors: ClassVar[list] = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


class Bookmark(models.Model):
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

    created = models.DateTimeField(auto_now_add=True)

    objects = BookmarkQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_episode",
                fields=["user", "episode"],
            )
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["-created"]),
        ]

    def __str__(self) -> str:
        """Required __str__ method"""
        return " | ".join(
            [
                f"user {self.user_id}",
                f"episode {self.episode_id}",
            ]
        )


class AudioLogQuerySet(SearchQuerySetMixin, models.QuerySet):
    """QuerySet for AudioLog."""

    search_vectors: ClassVar[list] = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


class AudioLog(models.Model):
    """Record of user listening history."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audio_logs",
    )
    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="audio_logs",
    )

    listened = models.DateTimeField()
    current_time = models.IntegerField(default=0)
    duration = models.IntegerField(default=0)

    objects: models.Manager["AudioLog"] = AudioLogQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_episode",
                fields=["user", "episode"],
            ),
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["-listened"]),
            models.Index(fields=["listened"]),
        ]

    def __str__(self) -> str:
        """Required __str__ method"""
        return " | ".join(
            [
                f"user {self.user_id}",
                f"episode {self.episode_id}",
            ]
        )

    @cached_property
    def percent_complete(self) -> int:
        """Returns percentage of episode listened to."""
        if 0 in {self.current_time, self.duration}:
            return 0

        return min(100, round((self.current_time / self.duration) * 100))
