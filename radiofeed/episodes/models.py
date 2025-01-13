from typing import ClassVar, Optional

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from fast_update.query import FastUpdateQuerySet

from radiofeed.html import strip_html
from radiofeed.search import SearchQuerySetMixin
from radiofeed.users.models import User


class EpisodeQuerySet(SearchQuerySetMixin, FastUpdateQuerySet):
    """QuerySet for Episode model."""

    def subscribed(self, user: User) -> models.QuerySet["Episode"]:
        """Returns episodes belonging to episodes subscribed by user."""
        return self.alias(
            is_subscribed=models.Exists(
                user.subscriptions.filter(
                    podcast=models.OuterRef("podcast"),
                )
            )
        ).filter(is_subscribed=True)


class Episode(models.Model):
    """Individual podcast episode."""

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

    website = models.URLField(max_length=2083, blank=True)

    episode_type = models.CharField(max_length=30, default="full")
    episode = models.IntegerField(null=True, blank=True)
    season = models.IntegerField(null=True, blank=True)

    cover_url = models.URLField(max_length=2083, blank=True)

    media_url = models.URLField(max_length=2083)
    media_type = models.CharField(max_length=60)

    length = models.BigIntegerField(null=True, blank=True)
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
        """Canonical episode URL."""
        return reverse(
            "episodes:episode_detail",
            kwargs={
                "episode_id": self.pk,
                "slug": self.slug,
            },
        )

    def get_next_episode(self) -> Optional["Episode"]:
        """Returns the next episode in this podcast."""
        try:
            return self.get_next_by_pub_date(podcast=self.podcast)
        except self.DoesNotExist:
            return None

    def get_previous_episode(self) -> Optional["Episode"]:
        """Returns the previous episode in this podcast."""
        try:
            return self.get_previous_by_pub_date(podcast=self.podcast)
        except self.DoesNotExist:
            return None

    def get_cover_url(self) -> str:
        """Returns cover image URL or podcast cover image if former not provided."""
        return self.cover_url or self.podcast.cover_url

    def get_episode_type(self) -> str | None:
        """Get the episode type (if not 'full')"""
        return (
            self.episode_type
            if self.episode_type and self.episode_type.casefold() != "full"
            else None
        )

    def get_file_size(self) -> str | None:
        """Returns human readable file size e.g. 30MB.

        If length is zero or none returns None.
        """
        return filesizeformat(self.length) if self.length else None

    def is_explicit(self) -> bool:
        """Check if either this specific episode or the podcast is explicit."""
        return self.explicit or self.podcast.explicit

    @cached_property
    def slug(self) -> str:
        """Returns slugified title, if any."""
        return slugify(self.title, allow_unicode=False) or "no-title"

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
                self.listened.isoformat(),
            ]
        )
