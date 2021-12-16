from __future__ import annotations

import mimetypes
import os

from datetime import datetime, timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.http import HttpRequest
from django.template.defaultfilters import filesizeformat
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from jcasts.podcasts.models import Podcast
from jcasts.shared.cleaners import strip_html
from jcasts.shared.db import FastCountMixin, SearchMixin
from jcasts.shared.typedefs import User

UNIQUE_CONSTRAINT = "unique_%(app_label)s_%(class)s"


class EpisodeQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    def with_current_time(self, user: User | AnonymousUser) -> models.QuerySet:

        """Adds `completed`, `current_time` and `listened` annotations."""

        if user.is_anonymous:
            return self.annotate(
                completed=models.Value(None, output_field=models.DateTimeField()),
                current_time=models.Value(0, output_field=models.IntegerField()),
                listened=models.Value(None, output_field=models.DateTimeField()),
            )

        logs = AudioLog.objects.filter(user=user, episode=models.OuterRef("pk"))

        return self.annotate(
            completed=models.Subquery(logs.values("completed")),
            current_time=models.Subquery(logs.values("current_time")),
            listened=models.Subquery(logs.values("updated")),
        )

    def recommended(
        self, user: User, since: timedelta = timedelta(days=7)
    ) -> models.QuerySet:
        """Return all episodes for podcasts the user is following,
        minus any the user has already queued/favorited/listened to."""

        if not (podcast_ids := set(user.follow_set.values_list("podcast", flat=True))):
            return self.none()

        min_pub_date = timezone.now() - since

        episodes = (
            self.filter(pub_date__gte=min_pub_date)
            .exclude(episode_type__iexact="trailer")
            .order_by("-pub_date", "-id")
        )

        if excluded := (
            set(AudioLog.objects.filter(user=user).values_list("episode", flat=True))
            | set(QueueItem.objects.filter(user=user).values_list("episode", flat=True))
            | set(Favorite.objects.filter(user=user).values_list("episode", flat=True))
        ):
            episodes = episodes.exclude(pk__in=excluded)

        episode_ids = set(
            Podcast.objects.filter(pk__in=podcast_ids, pub_date__gte=min_pub_date)
            .annotate(
                latest_episode=models.Subquery(
                    episodes.filter(podcast=models.OuterRef("pk")).values("pk")[:1]
                )
            )
            .values_list("latest_episode", flat=True)
        )

        return (
            self.filter(pk__in=episode_ids).distinct() if episode_ids else self.none()
        )

    def get_next_episode(self, episode: Episode) -> Episode | None:

        return (
            self.filter(
                podcast=episode.podcast_id,
                pub_date__gt=episode.pub_date,
            )
            .exclude(pk=episode.id)
            .order_by("pub_date")
            .first()
        )

    def get_previous_episode(self, episode: Episode) -> Episode | None:

        return (
            self.filter(
                podcast=episode.podcast_id,
                pub_date__lt=episode.pub_date,
            )
            .exclude(pk=episode.id)
            .order_by("-pub_date")
            .first()
        )


EpisodeManager = models.Manager.from_queryset(EpisodeQuerySet)


class Episode(models.Model):

    podcast: Podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

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

    objects = EpisodeManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name=UNIQUE_CONSTRAINT,
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
        return self.title or self.guid

    def get_absolute_url(self) -> str:
        return reverse("episodes:episode_detail", args=[self.pk, self.slug])

    @property
    def slug(self) -> str:
        return slugify(self.title, allow_unicode=False) or "no-title"

    def get_file_size(self) -> str | None:
        return filesizeformat(self.length) if self.length else None

    def get_cover_url(self) -> str | None:
        return self.cover_url or self.podcast.cover_url

    def get_actions_url(self) -> str:
        return reverse("episodes:actions", args=[self.id])

    def get_actions_tag(self) -> str:
        return f"episode-{self.id}"

    def is_queued(self, user: User | AnonymousUser) -> bool:
        if user.is_anonymous:
            return False
        return QueueItem.objects.filter(user=user, episode=self).exists()

    def is_favorited(self, user: User | AnonymousUser) -> bool:
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, episode=self).exists()

    @cached_property
    def cleaned_title(self) -> str:
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        return strip_html(self.description)

    @cached_property
    def current_time(self) -> int | None:
        raise AssertionError("use with QuerySet method 'with_current_time'")

    @cached_property
    def completed(self) -> datetime | None:
        raise AssertionError("use with QuerySet method 'with_current_time'")

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

    @cached_property
    def pc_complete(self) -> int:
        """Use with the `with_current_time` QuerySet method"""

        # if marked complete just assume 100% done
        if self.completed:
            return 100

        try:
            return min(round((self.current_time / self.duration_in_seconds) * 100), 100)
        except (TypeError, ZeroDivisionError):
            return 0

    @cached_property
    def time_remaining(self) -> int:
        return (
            self.duration_in_seconds - (self.current_time or 0)
            if self.duration_in_seconds
            else 0
        )

    @cached_property
    def is_completed(self) -> bool:
        """Use with the `with_current_time` QuerySet method"""
        return self.pc_complete > 99

    def get_opengraph_data(self, request: HttpRequest) -> dict:
        og_data = {
            "url": request.build_absolute_uri(self.get_absolute_url()),
            "title": f"{request.site.name} | {self.podcast.cleaned_title} | {self.cleaned_title}",
            "description": self.cleaned_description,
            "keywords": ", ".join(self.keywords.split()),
        }

        if cover_url := self.get_cover_url():
            og_data = {
                **og_data,
                "image": cover_url,
                "image_height": 200,
                "image_width": 200,
            }

        return og_data

    def get_episode_metadata(self) -> str:

        episode_type = (
            self.episode_type.capitalize()
            if self.episode_type and self.episode_type.lower() != "full"
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

    def get_media_url_ext(self) -> str:
        _, ext = os.path.splitext(urlparse(self.media_url).path)
        return ext[1:]

    def get_media_metadata(self) -> dict:
        # https://developers.google.com/web/updates/2017/02/media-session
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


class FavoriteQuerySet(SearchMixin, models.QuerySet):
    search_vectors: list[tuple[str, str]] = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


FavoriteManager = models.Manager.from_queryset(FavoriteQuerySet)


class Favorite(TimeStampedModel):

    user: User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode: Episode = models.ForeignKey(Episode, on_delete=models.CASCADE)

    objects = FavoriteManager()

    class Meta:

        constraints = [
            models.UniqueConstraint(
                name=UNIQUE_CONSTRAINT,
                fields=["user", "episode"],
            )
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]


class AudioLogQuerySet(SearchMixin, models.QuerySet):
    search_vectors: list[tuple[str, str]] = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


AudioLogManager = models.Manager.from_queryset(AudioLogQuerySet)


class AudioLog(TimeStampedModel):

    user: User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode: Episode = models.ForeignKey(Episode, on_delete=models.CASCADE)

    updated: datetime = models.DateTimeField()
    completed: datetime = models.DateTimeField(null=True, blank=True)
    current_time: int = models.IntegerField(default=0)

    objects = AudioLogManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name=UNIQUE_CONSTRAINT,
                fields=["user", "episode"],
            ),
        ]
        indexes = [
            models.Index(fields=["-updated"]),
            models.Index(fields=["updated"]),
        ]

    def to_json(self) -> dict:
        cover_url = self.episode.podcast.cover_url or static("img/podcast-icon.png")
        return {
            "currentTime": self.current_time,
            "episode": {
                "id": self.episode.id,
                "title": self.episode.title,
                "mediaUrl": self.episode.media_url,
                "url": self.episode.get_absolute_url(),
                "metadata": self.episode.get_media_metadata(),
            },
            "podcast": {
                "title": self.episode.podcast.title,
                "url": self.episode.podcast.get_absolute_url(),
                "coverImage": {
                    "width": 200,
                    "height": 200,
                    "url": cover_url,
                },
            },
        }


class QueueItemQuerySet(models.QuerySet):
    def create_item(self, user: User, episode: Episode) -> QueueItem:
        return self.create(
            episode=episode,
            user=user,
            position=(
                self.filter(user=user).aggregate(models.Max("position"))[
                    "position__max"
                ]
                or 0
            )
            + 1,
        )

    def move_items(self, user: User, item_ids: list[int]) -> None:
        qs = self.filter(user=user, pk__in=item_ids)

        items = qs.in_bulk()

        for_update = []

        for position, item_id in enumerate(item_ids, 1):
            if item := items.get(item_id):
                item.position = position
                for_update.append(item)

        return qs.bulk_update(for_update, ["position"])


QueueItemManager = models.Manager.from_queryset(QueueItemQuerySet)


class QueueItem(TimeStampedModel):
    user: User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode: Episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    position: int = models.IntegerField(default=0)

    objects = QueueItemManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name=UNIQUE_CONSTRAINT,
                fields=["user", "episode"],
            ),
        ]
        indexes = [
            models.Index(fields=["position"]),
        ]
