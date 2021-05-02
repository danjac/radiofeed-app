import dataclasses

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorField
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from audiotrails.podcasts.models import Podcast
from audiotrails.shared.db import FastCountMixin


@dataclasses.dataclass
class EpisodeDOM:

    episode: str
    favorite: str
    favorite_toggle: str
    history: str
    player_toggle: str
    queue: str
    queue_toggle: str
    remove_audio_log_btn: str


class EpisodeQuerySet(FastCountMixin, models.QuerySet):
    def with_current_time(self, user):

        """Adds `completed`, `current_time` and `listened` annotations."""

        if user.is_anonymous:
            return self.annotate(
                completed=models.Value(False, output_field=models.BooleanField()),
                current_time=models.Value(0, output_field=models.IntegerField()),
                listened=models.Value(None, output_field=models.DateTimeField()),
            )

        logs = AudioLog.objects.filter(user=user, episode=models.OuterRef("pk"))

        return self.annotate(
            completed=models.Subquery(logs.values("completed")),
            current_time=models.Subquery(logs.values("current_time")),
            listened=models.Subquery(logs.values("updated")),
        )

    def search(self, search_term):
        if not search_term:
            return self.none()

        query = SearchQuery(force_str(search_term), search_type="websearch")
        return self.annotate(
            rank=SearchRank(models.F("search_vector"), query=query)
        ).filter(search_vector=query)


EpisodeManager = models.Manager.from_queryset(EpisodeQuerySet)


class Episode(models.Model):

    podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    guid = models.TextField()

    pub_date = models.DateTimeField()
    link = models.URLField(null=True, blank=True, max_length=500)

    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)

    media_url = models.URLField(max_length=1000)
    media_type = models.CharField(max_length=60)
    length = models.BigIntegerField(null=True, blank=True)

    duration = models.CharField(max_length=30, blank=True)
    explicit = models.BooleanField(default=False)

    search_vector = SearchVectorField(null=True, editable=False)

    objects: models.Manager = EpisodeManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["podcast", "guid"], name="unique_episode")
        ]
        indexes = [
            models.Index(fields=["podcast", "pub_date"]),
            models.Index(fields=["podcast", "-pub_date"]),
            models.Index(fields=["podcast"]),
            models.Index(fields=["guid"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["-pub_date"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self):
        return self.title or self.guid

    def get_absolute_url(self):
        return reverse("episodes:episode_detail", args=[self.id, self.slug])

    def get_preview_url(self):
        return reverse("episodes:episode_preview", args=[self.id])

    @property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "episode"

    def get_file_size(self):
        return filesizeformat(self.length) if self.length else None

    @cached_property
    def dom(self):
        return EpisodeDOM(
            favorite=f"favorite-{self.id}",
            favorite_toggle=f"favorite-toggle-{self.id}",
            history=f"history-{self.id}",
            episode=f"episode-{self.id}",
            player_toggle=f"player-toggle-{self.id}",
            queue=f"queue-{self.id}",
            queue_toggle=f"queue-toggle-{self.id}",
            remove_audio_log_btn=f"remove-audio-log-btn-{self.id}",
        )

    def get_next_episode(self):
        try:
            return self.get_next_by_pub_date(podcast=self.podcast)
        except self.DoesNotExist:
            return None

    def get_previous_episode(self):
        try:
            return self.get_previous_by_pub_date(podcast=self.podcast)
        except self.DoesNotExist:
            return None

    def is_queued(self, user):
        if user.is_anonymous:
            return False
        return QueueItem.objects.filter(user=user, episode=self).exists()

    def is_favorited(self, user):
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, episode=self).exists()

    def get_duration_in_seconds(self):
        """Returns total number of seconds given string in [h:][m:]s format.
        Invalid formats return zero."""

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

    def get_pc_completed(self):
        """Use with the `with_current_time` QuerySet method"""

        try:
            # if marked complete just assume 100% done
            if self.completed:
                return 100

            if not self.current_time:
                return 0

            return min(
                ((self.current_time / self.get_duration_in_seconds()) * 100, 100)
            )

        except (ZeroDivisionError, AttributeError):
            return 0

    def is_completed(self):
        """Use with the `with_current_time` QuerySet method"""
        try:
            return self.completed or self.get_pc_completed() >= 100
        except AttributeError:
            return False

    def get_opengraph_data(self, request):
        og_data = {
            "url": request.build_absolute_uri(self.get_absolute_url()),
            "title": f"{request.site.name} | {self.podcast.title} | {self.title}",
            "description": self.description,
            "keywords": self.keywords,
        }

        if self.podcast.cover_image:
            og_data |= {
                "image": self.podcast.cover_image.url,
                "image_height": self.podcast.cover_image.height,
                "image_width": self.podcast.cover_image.width,
            }

        return og_data

    def get_media_metadata(self):
        # https://developers.google.com/web/updates/2017/02/media-session
        thumbnail = self.podcast.get_cover_image_thumbnail()

        return {
            "title": self.title,
            "album": self.podcast.title,
            "artist": self.podcast.creators,
            "artwork": [
                {
                    "src": thumbnail.url,
                    "sizes": f"{size}x{size}",
                    "type": "image/png",
                }
                for size in [96, 128, 192, 256, 384, 512]
            ],
        }


class FavoriteQuerySet(models.QuerySet):
    def search(self, search_term):
        if not search_term:
            return self.none()

        query = SearchQuery(force_str(search_term), search_type="websearch")
        return self.annotate(
            episode_rank=SearchRank(models.F("episode__search_vector"), query=query),
            podcast_rank=SearchRank(
                models.F("episode__podcast__search_vector"), query=query
            ),
            rank=models.F("episode_rank") + models.F("podcast_rank"),
        ).filter(
            models.Q(episode__search_vector=query)
            | models.Q(episode__podcast__search_vector=query)
        )


FavoriteManager = models.Manager.from_queryset(FavoriteQuerySet)


class Favorite(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)

    objects = FavoriteManager()

    class Meta:

        constraints = [
            models.UniqueConstraint(name="uniq_favorite", fields=["user", "episode"])
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]


class AudioLogQuerySet(models.QuerySet):
    def search(self, search_term):
        if not search_term:
            return self.none()

        query = SearchQuery(force_str(search_term), search_type="websearch")
        return self.annotate(
            episode_rank=SearchRank(models.F("episode__search_vector"), query=query),
            podcast_rank=SearchRank(
                models.F("episode__podcast__search_vector"), query=query
            ),
            rank=models.F("episode_rank") + models.F("podcast_rank"),
        ).filter(
            models.Q(episode__search_vector=query)
            | models.Q(episode__podcast__search_vector=query)
        )


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
            models.UniqueConstraint(name="uniq_audio_log", fields=["user", "episode"])
        ]
        indexes = [
            models.Index(fields=["-updated"]),
        ]

    def to_json(self):
        cover_image = self.episode.podcast.get_cover_image_thumbnail()
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
                    "width": cover_image.width,
                    "height": cover_image.height,
                    "url": cover_image.url,
                },
            },
        }


class QueueItemQuerySet(models.QuerySet):
    def with_current_time(self, user):
        """Adds current_time annotation."""
        return self.annotate(
            current_time=models.Subquery(
                AudioLog.objects.filter(
                    user=user, episode=models.OuterRef("episode")
                ).values("current_time")
            ),
        )


QueueItemManager = models.Manager.from_queryset(QueueItemQuerySet)


class QueueItem(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    objects = QueueItemManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(name="uniq_queue_item", fields=["user", "episode"]),
        ]
        indexes = [
            models.Index(fields=["position"]),
        ]
