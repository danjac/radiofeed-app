import os

from datetime import datetime, timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
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


class EpisodeQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    def with_current_time(self, user):

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

    def recommended(self, user, since=timedelta(days=7)):
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


EpisodeManager = models.Manager.from_queryset(EpisodeQuerySet)


class Episode(models.Model):

    podcast: Podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    guid = models.TextField()

    pub_date: datetime = models.DateTimeField()

    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)

    episode_type = models.CharField(max_length=30, default="full")
    episode = models.IntegerField(null=True, blank=True)
    season = models.IntegerField(null=True, blank=True)

    cover_url = models.URLField(max_length=2083, null=True, blank=True)

    media_url = models.URLField(max_length=2083)
    media_type = models.CharField(max_length=60)
    length = models.BigIntegerField(null=True, blank=True)

    duration = models.CharField(max_length=30, blank=True)
    explicit = models.BooleanField(default=False)

    search_vector = SearchVectorField(null=True, editable=False)

    objects = EpisodeManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
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

    def __str__(self):
        return self.title or self.guid

    def get_absolute_url(self):
        return reverse("episodes:episode_detail", args=[self.pk, self.slug])

    @cached_property
    def cleaned_title(self):
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self):
        return strip_html(self.description)

    @property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "episode"

    def get_file_size(self):
        return filesizeformat(self.length) if self.length else None

    def get_cover_url(self):
        return self.cover_url or self.podcast.cover_url

    def get_next_episode(self):

        return (
            self.__class__._default_manager.filter(
                podcast=self.podcast,
                pub_date__gt=self.pub_date,
            )
            .order_by("pub_date")
            .first()
        )

    def get_previous_episode(self):

        return (
            self.__class__._default_manager.filter(
                podcast=self.podcast,
                pub_date__lt=self.pub_date,
            )
            .order_by("-pub_date")
            .first()
        )

    def is_queued(self, user):
        if user.is_anonymous:
            return False
        return QueueItem.objects.filter(user=user, episode=self).exists()

    def is_favorited(self, user):
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, episode=self).exists()

    def get_current_time(self):
        """Return current_time if annotated in QuerySet `with_current_time` method"""
        return getattr(self, "current_time", None) or 0

    def get_completed(self):
        """Return completed if annotated in QuerySet `with_current_time` method"""
        return getattr(self, "completed", None)

    @cached_property
    def duration_in_seconds(self):
        """Returns total number of seconds given string in [h:][m:]s format.
        Invalid formats return None."""

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
    def pc_complete(self):
        """Use with the `with_current_time` QuerySet method"""

        # if marked complete just assume 100% done
        if self.get_completed():
            return 100

        try:
            return min(
                round((self.get_current_time() / self.duration_in_seconds) * 100), 100
            )
        except ZeroDivisionError:
            return 0

    @cached_property
    def time_remaining(self):
        return (
            self.duration_in_seconds - self.get_current_time()
            if self.duration_in_seconds
            else 0
        )

    @cached_property
    def is_completed(self):
        """Use with the `with_current_time` QuerySet method"""
        return self.pc_complete > 99

    def get_opengraph_data(self, request):
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

    def get_episode_metadata(self):

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

    def get_media_url_ext(self):
        _, ext = os.path.splitext(urlparse(self.media_url).path)
        return ext[1:]

    def get_media_metadata(self):
        # https://developers.google.com/web/updates/2017/02/media-session
        cover_url = self.get_cover_url() or static("img/podcast-icon.png")

        return {
            "title": self.cleaned_title,
            "album": self.podcast.cleaned_title,
            "artist": self.podcast.owner,
            "artwork": [
                {
                    "src": cover_url,
                    "sizes": f"{size}x{size}",
                    "type": "image/png",
                }
                for size in [96, 128, 192, 256, 384, 512]
            ],
        }


class FavoriteQuerySet(SearchMixin, models.QuerySet):
    search_vectors = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


FavoriteManager = models.Manager.from_queryset(FavoriteQuerySet)


class Favorite(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode: Episode = models.ForeignKey(Episode, on_delete=models.CASCADE)

    objects = FavoriteManager()

    class Meta:

        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["user", "episode"],
            )
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]


class AudioLogQuerySet(SearchMixin, models.QuerySet):
    search_vectors = [
        ("episode__search_vector", "episode_rank"),
        ("episode__podcast__search_vector", "podcast_rank"),
    ]


AudioLogManager = models.Manager.from_queryset(AudioLogQuerySet)


class AudioLog(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)

    updated = models.DateTimeField()
    completed = models.DateTimeField(null=True, blank=True)
    current_time = models.IntegerField(default=0)

    objects = AudioLogManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["user", "episode"],
            ),
        ]
        indexes = [
            models.Index(fields=["-updated"]),
            models.Index(fields=["updated"]),
        ]

    def to_json(self):
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
    def add_item_to_start(self, user, episode):
        self.filter(user=user).update(position=models.F("position") + 1)
        return self.create(episode=episode, user=user, position=1)

    def add_item_to_end(self, user, episode):
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

    def move_items(self, user, item_ids):
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    objects = QueueItemManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["user", "episode"],
            ),
        ]
        indexes = [
            models.Index(fields=["position"]),
        ]
