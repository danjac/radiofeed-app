# Django
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorField
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# Third Party Libraries
from model_utils.models import TimeStampedModel

# RadioFeed
from radiofeed.podcasts.models import Podcast


class EpisodeQuerySet(models.QuerySet):
    def with_current_time(self, user):
        if user.is_anonymous:
            return self.annotate(
                current_time=models.Value(0, output_field=models.IntegerField())
            )
        return self.annotate(
            current_time=models.Subquery(
                History.objects.filter(user=user, episode=models.OuterRef("pk")).values(
                    "current_time"
                )
            )
        )

    def search(self, search_term):
        if not search_term:
            return self.none()

        query = SearchQuery(search_term)
        return self.annotate(
            rank=SearchRank(models.F("search_vector"), query=query)
        ).filter(search_vector=query)


class EpisodeManager(models.Manager.from_queryset(EpisodeQuerySet)):
    ...


class Episode(models.Model):

    podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    guid = models.TextField()

    pub_date = models.DateTimeField()
    link = models.URLField(null=True, blank=True, max_length=500)

    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)

    media_url = models.URLField(max_length=500)
    media_type = models.CharField(max_length=60)
    length = models.IntegerField(null=True, blank=True)

    duration = models.CharField(max_length=30, blank=True)
    explicit = models.BooleanField(default=False)

    search_vector = SearchVectorField(null=True, editable=False)

    objects = EpisodeManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["podcast", "guid"], name="unique_episode")
        ]
        indexes = [
            models.Index(fields=["podcast"]),
            models.Index(fields=["guid"]),
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self):
        return self.title or self.guid

    def get_absolute_url(self):
        return reverse("episodes:episode_detail", args=[self.id, self.slug])

    @property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "episode"

    @property
    def file_size(self):
        return filesizeformat(self.length) if self.length else None

    def log_activity(self, user, current_time=0, mark_complete=False):
        # Updates history log with current time
        if user.is_anonymous:
            return (None, False)
        now = timezone.now()
        return History.objects.update_or_create(
            episode=self,
            user=user,
            defaults={
                "current_time": current_time,
                "updated": now,
                "completed": now if mark_complete else None,
            },
        )


class BookmarkQuerySet(models.QuerySet):
    def search(self, search_term):
        if not search_term:
            return self.none()

        query = SearchQuery(search_term)
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


class BookmarkManager(models.Manager.from_queryset(BookmarkQuerySet)):
    ...


class Bookmark(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)

    objects = BookmarkManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(name="uniq_bookmark", fields=["user", "episode"])
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]


class History(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    updated = models.DateTimeField()
    completed = models.DateTimeField(null=True, blank=True)
    current_time = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(name="uniq_history", fields=["user", "episode"])
        ]
        indexes = [
            models.Index(fields=["-updated"]),
            models.Index(fields=["-completed"]),
        ]
