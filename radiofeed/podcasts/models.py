from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from radiofeed import cleaners
from radiofeed.fast_count import FastCountQuerySetMixin
from radiofeed.search import SearchQuerySetMixin

if TYPE_CHECKING:  # pragma: no cover
    import decimal
    from datetime import datetime

    from radiofeed.users.models import User


class CategoryQuerySet(models.QuerySet):
    """Custom QuerySet for Category model."""

    def search(self, search_term: str) -> models.QuerySet[Category]:
        """Does a simple search for categories."""
        if value := force_str(search_term):
            return self.filter(name__icontains=value)
        return self.none()


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

    objects: models.Manager[Category] = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self) -> str:
        """Returns category name."""
        return self.name

    def get_absolute_url(self) -> str:
        """Absolute URL to a category."""
        return reverse("podcasts:category_detail", args=[self.pk, self.slug])

    @property
    def slug(self) -> str:
        """Returns slugified name."""
        return slugify(self.name, allow_unicode=False)


class PodcastQuerySet(
    FastCountQuerySetMixin,
    SearchQuerySetMixin,
    models.QuerySet,
):
    """Custom QuerySet of Podcast model."""

    def search(self, search_term: str) -> models.QuerySet[Podcast]:
        """Does standard full text search, prioritizing exact search results.

        Annotates `exact_match` to indicate such results.
        """
        if not search_term:
            return self.none()

        qs = super().search(search_term)

        if exact_matches := set(
            self.alias(title_lower=models.functions.Lower("title"))
            .filter(title_lower=force_str(search_term).casefold())
            .values_list("pk", flat=True)
        ):
            qs = qs | self.filter(pk__in=exact_matches)
            return qs.annotate(
                exact_match=models.Case(
                    models.When(pk__in=exact_matches, then=models.Value(1)),
                    default=models.Value(0),
                )
            ).distinct()
        return qs.annotate(exact_match=models.Value(0))


class Podcast(models.Model):
    """Podcast channel or feed."""

    class ParserError(models.TextChoices):
        DUPLICATE = "duplicate", "Duplicate"
        INACCESSIBLE = "inaccessible", "Inaccessible"
        INVALID_RSS = "invalid_rss", "Invalid RSS"
        NOT_MODIFIED = "not_modified", "Not Modified"
        UNAVAILABLE = "unavailable", "Unavailable"

    rss: str = models.URLField(unique=True, max_length=500)

    active: bool = models.BooleanField(
        default=True,
        help_text="Inactive podcasts will no longer be updated from their RSS feeds.",
    )

    private: bool = models.BooleanField(
        default=False,
        help_text="Only available to subscribers",
    )

    etag: str = models.TextField(blank=True)
    title: str = models.TextField(blank=True)

    pub_date: datetime | None = models.DateTimeField(null=True, blank=True)

    parsed: datetime | None = models.DateTimeField(null=True, blank=True)

    parser_error: str = models.CharField(
        max_length=30,
        choices=ParserError.choices,
        null=True,
        blank=True,
    )

    frequency: timedelta = models.DurationField(
        default=timedelta(hours=24),
    )

    modified: datetime | None = models.DateTimeField(
        null=True,
        blank=True,
    )

    content_hash: str | None = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )

    num_retries: int = models.PositiveSmallIntegerField(default=0)

    cover_url: str | None = models.URLField(max_length=2083, null=True, blank=True)

    funding_url: str | None = models.URLField(max_length=2083, null=True, blank=True)
    funding_text: str = models.TextField(blank=True)

    language: str = models.CharField(
        max_length=2,
        default="en",
        validators=[MinLengthValidator(2)],
    )

    description: str = models.TextField(blank=True)
    website: str | None = models.URLField(max_length=2083, null=True, blank=True)
    keywords: str = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    owner: str = models.TextField(blank=True)

    created: datetime = models.DateTimeField(auto_now_add=True)
    updated: datetime = models.DateTimeField(
        auto_now=True, verbose_name="Podcast Updated in Database"
    )

    explicit: bool = models.BooleanField(default=False)
    promoted: bool = models.BooleanField(default=False)

    categories: models.QuerySet[Category] = models.ManyToManyField(
        "podcasts.Category",
        blank=True,
        related_name="podcasts",
    )

    recipients: models.QuerySet[User] = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="recommended_podcasts",
    )

    search_vector: str | None = SearchVectorField(null=True, editable=False)

    objects: models.Manager[Podcast] = PodcastQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["promoted"]),
            models.Index(fields=["content_hash"]),
            models.Index(
                models.functions.Lower("title"),
                name="%(app_label)s_%(class)s_lwr_title_idx",
            ),
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
        return cleaners.strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        """Strips HTML from description field."""
        return cleaners.strip_html(self.description)

    @cached_property
    def slug(self) -> str:
        """Returns slugified title."""
        return slugify(self.title, allow_unicode=False) or "no-title"


class Subscription(TimeStampedModel):
    """Subscribed podcast belonging to a user's collection."""

    subscriber: User = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_podcast",
                fields=["subscriber", "podcast"],
            )
        ]
        indexes = [models.Index(fields=["-created"])]


class RecommendationQuerySet(models.QuerySet):
    """Custom QuerySet for Recommendation model."""

    def with_relevance(self) -> models.QuerySet[Recommendation]:
        """Returns factor of frequency and similarity as annotated value `relevance`."""
        return self.annotate(relevance=models.F("frequency") * models.F("similarity"))

    def bulk_delete(self) -> int:
        """More efficient quick delete.

        Returns:
            number of rows deleted
        """
        return self._raw_delete(self.db)


class Recommendation(models.Model):
    """Recommendation based on similarity between two podcasts."""

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    recommended: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="similar",
    )

    frequency: int = models.PositiveIntegerField(default=0)

    similarity: decimal.Decimal | None = models.DecimalField(
        decimal_places=10,
        max_digits=100,
        null=True,
        blank=True,
    )

    objects: models.Manager[Recommendation] = RecommendationQuerySet.as_manager()

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

    def __str__(self) -> str:
        """Returns ID of recommendation."""
        return f"Recommendation #{self.pk}"
