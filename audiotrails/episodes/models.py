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
from sorl.thumbnail import get_thumbnail

from audiotrails.db import FastCountMixin
from audiotrails.podcasts.models import Podcast


@dataclasses.dataclass
class EpisodeDOM:

    episode: str
    favorite: str
    favorite_toggle: str
    history: str
    player_toggle: str
    queue: str
    queue_toggle: str


class EpisodeQuerySet(FastCountMixin, models.QuerySet):
    def latest_episodes(self, user):

        if user.is_authenticated:
            podcast_ids = list(user.follow_set.values_list("podcast", flat=True))
            listened_ids = list(
                AudioLog.objects.for_user(user).values_list("episode", flat=True)
            )
        else:
            podcast_ids, listened_ids = [], []

        if podcast_ids:
            show_promoted = False

        else:
            podcast_ids = list(
                Podcast.objects.filter(promoted=True).values_list("pk", flat=True)
            )
            show_promoted = True

        # we want a list of the *latest* episode for each podcast
        latest_episodes = (
            Episode.objects.filter(podcast=models.OuterRef("pk"))
            .order_by("-pub_date")
            .distinct()
        )

        if listened_ids:
            latest_episodes = latest_episodes.exclude(pk__in=listened_ids)

        episode_ids = (
            Podcast.objects.filter(pk__in=podcast_ids)
            .annotate(latest_episode=models.Subquery(latest_episodes.values("pk")[:1]))
            .values_list("latest_episode", flat=True)
            .distinct()
        )

        return (
            Episode.objects.select_related("podcast")
            .filter(pk__in=set(episode_ids))
            .order_by("-pub_date")
            .distinct()
        ), show_promoted

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
        data = {
            "title": self.title,
            "album": self.podcast.title,
            "artist": self.podcast.creators,
        }

        if self.podcast.cover_image:
            thumbnail = get_thumbnail(
                self.podcast.cover_image, "200", format="WEBP", crop="center"
            )

            if thumbnail:
                data |= {
                    "artwork": [
                        {
                            "src": thumbnail.url,
                            "sizes": f"{size}x{size}",
                            "type": "image/png",
                        }
                        for size in [96, 128, 192, 256, 384, 512]
                    ]
                }

        return data


class FavoriteQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.is_anonymous:
            return self.none()
        return self.filter(user=user)

    def create_favorite(self, user, episode):
        return self.create(user=user, episode=episode), self.for_user(user).count()

    def delete_favorite(self, user, episode):
        qs = self.for_user(user)
        qs.filter(episode=episode).delete()
        return qs.count()

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
    def for_user(self, user):
        if user.is_anonymous:
            return self.none()
        return self.filter(user=user)

    def delete_log(self, user, episode):
        qs = self.for_user(user)
        qs.filter(episode=episode).delete()
        return qs.count()

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


class QueueItemQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.is_anonymous:
            return self.none()
        return self.filter(user=user)

    def create_item(self, user, episode):
        return (
            self.create(
                user=user,
                episode=episode,
                position=(
                    self.for_user(user).aggregate(models.Max("position"))[
                        "position__max"
                    ]
                    or 0
                )
                + 1,
            ),
            self.for_user(user).count(),
        )

    def delete_item(self, user, episode):
        items = self.for_user(user)
        items.filter(episode=episode).delete()
        return items.count()

    def move_items(self, user, item_ids):
        qs = self.for_user(user)
        items = qs.in_bulk()
        for_update = []

        for position, item_id in enumerate(
            [item_id for item_id in item_ids if item_id in items], 1
        ):
            item = items[item_id]
            item.position = position
            for_update.append(item)
        return qs.bulk_update(for_update, ["position"])

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
