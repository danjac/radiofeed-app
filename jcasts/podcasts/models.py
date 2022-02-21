from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, TrigramSimilarity
from django.core.validators import MinLengthValidator
from django.db import models
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from jcasts.common.cleaners import strip_html
from jcasts.common.db import FastCountMixin, SearchMixin
from jcasts.common.typedefs import User


class CategoryQuerySet(models.QuerySet):
    def search(self, search_term: str, base_similarity: float = 0.2) -> models.QuerySet:
        return self.annotate(
            similarity=TrigramSimilarity("name", force_str(search_term))
        ).filter(similarity__gte=base_similarity)


CategoryManager = models.Manager.from_queryset(CategoryQuerySet)


class Category(models.Model):

    name: str = models.CharField(max_length=100, unique=True)
    parent: Category | None = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    objects = CategoryManager()

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @property
    def slug(self) -> str:
        return slugify(self.name, allow_unicode=False)

    def get_absolute_url(self) -> str:
        return reverse("podcasts:category_detail", args=[self.pk, self.slug])


class PodcastQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    def with_subscribed(self) -> models.QuerySet:
        return self.annotate(
            subscribed=models.Exists(
                Subscription.objects.filter(podcast=models.OuterRef("pk"))
            )
        )


PodcastManager = models.Manager.from_queryset(PodcastQuerySet)


class Podcast(models.Model):
    class Result(models.TextChoices):
        DUPLICATE_FEED = "duplicate_feed", "Duplicate Feed"
        HTTP_ERROR = "http_error", "HTTP Error"
        INVALID_RSS = "invalid_rss", "Invalid RSS"
        NETWORK_ERROR = "network_error", "Network Error"
        NOT_MODIFIED = "not_modified", "Not Modified"
        SUCCESS = "success", "Success"

    rss: str = models.URLField(unique=True, max_length=500)
    active: bool = models.BooleanField(default=True)

    etag: str = models.TextField(blank=True)
    title: str = models.TextField()

    # latest episode pub date from RSS feed
    pub_date: datetime | None = models.DateTimeField(null=True, blank=True)

    # last parse time (success or fail)
    parsed: datetime | None = models.DateTimeField(null=True, blank=True)

    # has been queued for parsing
    queued: datetime | None = models.DateTimeField(null=True, blank=True)

    # rq
    feed_queue: str | None = models.CharField(max_length=30, null=True, blank=True)

    # Last-Modified header from RSS feed
    modified: datetime | None = models.DateTimeField(null=True, blank=True)

    # feed parse result fields

    result: str | None = models.CharField(
        max_length=20, choices=Result.choices, null=True, blank=True
    )

    # hash of last polled content
    content_hash: str | None = models.CharField(max_length=64, null=True, blank=True)

    http_status: int | None = models.SmallIntegerField(null=True, blank=True)

    errors: int = models.PositiveIntegerField(default=0)

    cover_url: str | None = models.URLField(max_length=2083, null=True, blank=True)

    funding_url: str | None = models.URLField(max_length=2083, null=True, blank=True)
    funding_text: str = models.TextField(blank=True)

    language: str = models.CharField(
        max_length=2, default="en", validators=[MinLengthValidator(2)]
    )
    description: str = models.TextField(blank=True)
    link: str | None = models.URLField(max_length=2083, null=True, blank=True)
    keywords: str = models.TextField(blank=True)
    extracted_text: str = models.TextField(blank=True)
    owner: str = models.TextField(blank=True)

    created: datetime = models.DateTimeField(auto_now_add=True)
    updated: datetime = models.DateTimeField(auto_now=True)

    explicit: bool = models.BooleanField(default=False)
    promoted: bool = models.BooleanField(default=False)

    categories: list[Category] = models.ManyToManyField(Category, blank=True)

    # received recommendation email
    recipients: list[User] = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="recommended_podcasts",
    )

    search_vector: str | None = SearchVectorField(null=True, editable=False)

    objects = PodcastManager()

    class Meta:
        indexes = [
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["promoted"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self) -> str:
        return self.title or self.rss

    def get_absolute_url(self) -> str:
        return self.get_detail_url()

    def get_detail_url(self) -> str:
        return reverse("podcasts:podcast_detail", args=[self.pk, self.slug])

    def get_episodes_url(self) -> str:
        return reverse("podcasts:podcast_episodes", args=[self.pk, self.slug])

    def get_similar_url(self) -> str:
        return reverse("podcasts:podcast_similar", args=[self.pk, self.slug])

    def get_latest_episode_url(self) -> str:
        return reverse("podcasts:latest_episode", args=[self.pk])

    def get_domain(self) -> str:
        return urlparse(self.rss).netloc.rsplit("www.", 1)[-1]

    @cached_property
    def cleaned_title(self) -> str:
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        return strip_html(self.description)

    @cached_property
    def slug(self) -> str:
        return slugify(self.title, allow_unicode=False) or "no-title"

    def is_subscribed(self, user: User | AnonymousUser) -> bool:
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(podcast=self, user=user).exists()

    def get_opengraph_data(self, request: HttpRequest) -> dict:

        og_data = {
            "url": request.build_absolute_uri(self.get_absolute_url()),
            "title": f"{request.site.name} | {self.cleaned_title}",
            "description": self.cleaned_description,
            "keywords": ", ".join(self.keywords.split()),
        }

        if self.cover_url:
            og_data = {
                **og_data,
                "image": self.cover_url,
                "image_height": 200,
                "image_width": 200,
            }
        return og_data


class Subscription(TimeStampedModel):

    user: User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    podcast: Podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["user", "podcast"],
            )
        ]
        indexes = [models.Index(fields=["-created"])]


class RecommendationQuerySet(models.QuerySet):
    def bulk_delete(self) -> int:
        """More efficient quick delete"""
        return self._raw_delete(self.db)

    def for_user(self, user: User) -> models.QuerySet:
        podcast_ids: set[int] = (
            set(
                user.bookmark_set.select_related("episode__podcast").values_list(
                    "episode__podcast", flat=True
                )
            )
            | set(
                user.audiolog_set.select_related("episode__podcast").values_list(
                    "episode__podcast", flat=True
                )
            )
            | set(user.subscription_set.values_list("podcast", flat=True))
        )

        return self.filter(podcast__pk__in=podcast_ids).exclude(
            recommended__pk__in=podcast_ids
            | set(user.recommended_podcasts.distinct().values_list("pk", flat=True))
        )


RecommendationManager = models.Manager.from_queryset(RecommendationQuerySet)


class Recommendation(models.Model):

    podcast: Podcast = models.ForeignKey(
        Podcast, related_name="+", on_delete=models.CASCADE
    )
    recommended: Podcast = models.ForeignKey(
        Podcast, related_name="+", on_delete=models.CASCADE
    )

    frequency: int = models.PositiveIntegerField(default=0)

    similarity: Decimal = models.DecimalField(
        decimal_places=10, max_digits=100, null=True, blank=True
    )

    objects = RecommendationManager()

    class Meta:
        indexes = [
            models.Index(fields=["podcast"]),
            models.Index(fields=["recommended"]),
            models.Index(fields=["-similarity", "-frequency"]),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["podcast", "recommended"],
            ),
        ]
