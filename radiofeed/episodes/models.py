# Django
from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.text import slugify

# Third Party Libraries
from model_utils.models import TimeStampedModel

# RadioFeed
from radiofeed.podcasts.models import Podcast


class EpisodeQuerySet(models.QuerySet):
    def search(self, search_term, base_similarity=0.1):
        return self.annotate(similarity=TrigramSimilarity("title", search_term)).filter(
            similarity__gte=base_similarity
        )


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
    media_type = models.CharField(max_length=20)
    length = models.IntegerField(null=True, blank=True)

    duration = models.CharField(max_length=12, blank=True)
    explicit = models.BooleanField(default=False)

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
            models.Index(fields=["title"]),
            models.Index(fields=["-title"]),
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


class BookmarkQuerySet(models.QuerySet):
    def search(self, search_term, base_similarity=0.1):
        return self.annotate(
            similarity=TrigramSimilarity("episode__title", search_term)
        ).filter(similarity__gte=base_similarity)


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
        indexes = [models.Index(fields=["-created"])]
