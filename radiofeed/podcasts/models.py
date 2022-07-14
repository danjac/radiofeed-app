from __future__ import annotations

import decimal

from datetime import datetime, timedelta
from typing import final

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, TrigramSimilarity
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

from radiofeed.common.db import FastCountMixin, SearchMixin
from radiofeed.common.utils.html import strip_html
from radiofeed.users.models import User


@final
class CategoryQuerySet(models.QuerySet):
    """Custom QuerySet for Category model."""

    def search(
        self, search_term: str, base_similarity: float = 0.2
    ) -> models.QuerySet[Category]:
        """Does a trigram similarity search for categories."""
        return self.annotate(
            similarity=TrigramSimilarity("name", force_str(search_term))
        ).filter(similarity__gte=base_similarity)


@final
class Category(models.Model):
    """iTunes category."""

    name: str = models.CharField(max_length=100, unique=True)
    parent: Category | None = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    objects: models.Manager["Category"] = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self) -> str:
        """Returns category name."""
        return self.name

    @property
    def slug(self) -> str:
        """Returns slugified name."""
        return slugify(self.name, allow_unicode=False)

    def get_absolute_url(self) -> str:
        """Absolute URL to a category."""
        return reverse("podcasts:category_detail", args=[self.pk, self.slug])


@final
class PodcastQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    """Custom QuerySet of Podcast model."""

    def scheduled(self) -> models.QuerySet[Podcast]:
        """Returns podcasts scheduled for update.

        Scheduling algorithm:

            1. check once every n hours, where "n" is the number of days since the podcast was last updated (i.e. last pub date).
            2. if podcast was last updated within 24 hours, check once an hour.
            3. if podcast was last updated > 24 days, check every 24 hours.
            4. if podcast has not been checked yet (i.e. just added to database), check immediately.

        Only *active* podcasts should be included.
        """
        now = timezone.now()

        return Podcast.objects.annotate(
            days_since_last_pub_date=models.functions.ExtractDay(
                now - models.F("pub_date")
            ),
        ).filter(
            models.Q(
                parsed__isnull=True,
            )
            | models.Q(
                pub_date__isnull=True,
            )
            | models.Q(
                days_since_last_pub_date__lt=1,
                parsed__lt=now - timedelta(hours=1),
            )
            | models.Q(
                days_since_last_pub_date__gt=24,
                parsed__lt=now - timedelta(hours=24),
            )
            | models.Q(
                days_since_last_pub_date__range=(1, 24),
                parsed__lt=now
                - timedelta(hours=1) * models.F("days_since_last_pub_date"),
            ),
            active=True,
        )


@final
class Podcast(models.Model):
    """Podcast channel or feed."""

    class ParseResult(models.TextChoices):
        """Result of feed parser process."""

        SUCCESS = "success", _("Success")
        COMPLETE = "complete", _("Complete")
        NOT_MODIFIED = "not_modified", _("Not Modified")
        HTTP_ERROR = "http_error", _("HTTP Error")
        RSS_PARSER_ERROR = "rss_parser_error", _("RSS Parser Error")
        DUPLICATE_FEED = "duplicate_feed", _("Duplicate Feed")

    rss: str = models.URLField(unique=True, max_length=500)
    active: bool = models.BooleanField(default=True)

    etag: str = models.TextField(blank=True)
    title: str = models.TextField()

    # latest episode pub date from RSS feed
    pub_date: datetime | None = models.DateTimeField(null=True, blank=True)

    # last parse time (success or fail)
    parsed: datetime | None = models.DateTimeField(null=True, blank=True)

    # Last-Modified header from RSS feed
    modified: datetime | None = models.DateTimeField(null=True, blank=True)

    # hash of last polled content
    content_hash: str | None = models.CharField(max_length=64, null=True, blank=True)

    http_status: int | None = models.SmallIntegerField(null=True, blank=True)

    parse_result: str = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        choices=ParseResult.choices,
    )

    num_retries: int = models.PositiveSmallIntegerField(default=0)

    cover_url: str | None = models.URLField(max_length=2083, null=True, blank=True)

    funding_url: str | None = models.URLField(max_length=2083, null=True, blank=True)
    funding_text: str = models.TextField(blank=True)

    language: str = models.CharField(
        max_length=2, default="en", validators=[MinLengthValidator(2)]
    )

    description: str = models.TextField(blank=True)
    link: str | None = models.URLField(max_length=2083, null=True, blank=True)
    keywords: str = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    owner: str = models.TextField(blank=True)

    created: datetime = models.DateTimeField(auto_now_add=True)
    updated: datetime = models.DateTimeField(auto_now=True)

    explicit: bool = models.BooleanField(default=False)
    promoted: bool = models.BooleanField(default=False)

    categories: models.QuerySet[Category] = models.ManyToManyField(
        "podcasts.Category", blank=True
    )

    # received recommendation email
    recipients: models.QuerySet[User] = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="recommended_podcasts",
    )

    search_vector: str | None = SearchVectorField(null=True, editable=False)

    objects: models.Manager["Podcast"] = PodcastQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["promoted"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self) -> str:
        """Returns podcast title or RSS if missing."""
        return self.title or self.rss

    def get_absolute_url(self) -> str:
        """Default absolute URL of podcast."""
        return self.get_detail_url()

    def get_detail_url(self) -> str:
        """Absolute URL of podcast detail page."""
        return reverse("podcasts:podcast_detail", args=[self.pk, self.slug])

    def get_episodes_url(self) -> str:
        """Absolute URL of podcast episode list page."""
        return reverse("podcasts:podcast_episodes", args=[self.pk, self.slug])

    def get_similar_url(self) -> str:
        """Absolute URL of podcast similar recommendations page."""
        return reverse("podcasts:podcast_similar", args=[self.pk, self.slug])

    def get_latest_episode_url(self) -> str:
        """Absolute URL to latest episode redirect."""
        return reverse("podcasts:latest_episode", args=[self.pk, self.slug])

    @cached_property
    def cleaned_title(self) -> str:
        """Strips HTML from title field."""
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        """Strips HTML from description field."""
        return strip_html(self.description)

    @cached_property
    def slug(self) -> str:
        """Returns slugified title."""
        return slugify(self.title, allow_unicode=False) or "no-title"

    def is_subscribed(self, user: User | AnonymousUser) -> bool:
        """Check if user is subscribed to this podcast."""
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(podcast=self, user=user).exists()

    def get_subscribe_target(self) -> str:
        """Returns HTMX subscribe action target."""
        return f"subscribe-actions-{self.id}"


@final
class Subscription(TimeStampedModel):
    """Subscribed podcast belonging to a user's collection."""

    user: User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    podcast: Podcast = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_podcast",
                fields=["user", "podcast"],
            )
        ]
        indexes = [models.Index(fields=["-created"])]


@final
class RecommendationQuerySet(models.QuerySet):
    """Custom QuerySet for Recommendation model."""

    def bulk_delete(self) -> int:
        """More efficient quick delete.

        Returns:
            number of rows deleted
        """
        return self._raw_delete(self.db)


@final
class Recommendation(models.Model):
    """Recommendation based on similarity between two podcasts."""

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        related_name="+",
        on_delete=models.CASCADE,
    )

    recommended: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        related_name="+",
        on_delete=models.CASCADE,
    )

    frequency: int = models.PositiveIntegerField(default=0)

    similarity: decimal.Decimal | None = models.DecimalField(
        decimal_places=10, max_digits=100, null=True, blank=True
    )

    objects: models.Manager["Recommendation"] = RecommendationQuerySet.as_manager()

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
