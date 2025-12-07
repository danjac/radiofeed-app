import dataclasses
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar, Final, Self

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from slugify import slugify

from listenwave.fields import URLField
from listenwave.sanitizer import strip_html
from listenwave.search import SearchableMixin
from listenwave.users.models import User

if TYPE_CHECKING:
    from listenwave.episodes.models import EpisodeQuerySet


@dataclasses.dataclass(kw_only=True, frozen=True)
class Season:
    """Encapsulates podcast season"""

    podcast: "Podcast"
    season: int

    def __str__(self) -> str:
        """Return season label."""
        return self.label

    @cached_property
    def label(self) -> str:
        """Returns label for season."""
        return f"Season {self.season}"

    @cached_property
    def url(self) -> str:
        """Returns URL of season."""
        return reverse(
            "podcasts:season",
            kwargs={
                "podcast_id": self.podcast.pk,
                "slug": self.podcast.slug,
                "season": self.season,
            },
        )


class CategoryQuerySet(models.QuerySet):
    """Custom QuerySet for Category model."""

    def search(self, search_term) -> Self:
        """Does a simple search for categories."""
        if value := force_str(search_term):
            return self.filter(name__icontains=value)
        return self.none()


class Category(models.Model):
    """iTunes category."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    itunes_genre_id = models.PositiveIntegerField(null=True, blank=True)

    objects: CategoryQuerySet = CategoryQuerySet.as_manager()  # type: ignore[assignment]

    if TYPE_CHECKING:
        podcasts: "PodcastQuerySet"

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)
        indexes: ClassVar[list] = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        """Returns category name."""
        return self.name

    def save(self, **kwargs) -> None:
        """Overrides save to auto-generate slug."""
        self.slug = slugify(self.name, allow_unicode=False)
        super().save(**kwargs)

    def get_absolute_url(self) -> str:
        """Absolute URL to a category."""
        return reverse("podcasts:category_detail", kwargs={"slug": self.slug})


class PodcastQuerySet(SearchableMixin, models.QuerySet):
    """Custom QuerySet of Podcast model."""

    def subscribed(self, user: User) -> Self:
        """Returns podcasts subscribed by user."""
        return self.filter(pk__in=user.subscriptions.values("podcast"))

    def published(self, *, published: bool = True) -> Self:
        """Returns only published podcasts (pub_date NOT NULL)."""
        return self.filter(pub_date__isnull=not published)

    def scheduled(self) -> Self:
        """Returns all podcasts scheduled for feed parser update.

        1. If parsed is NULL, should be ASAP.
        2. If pub date is NULL, if NOW - frequency > parsed
        3. If pub date is not NULL, if NOW - frequency > pub date
        4. If parsed more than 3 days ago

        Last parsed time must be at least one hour.
        """
        now = timezone.now()
        since = now - models.F("frequency")  # type: ignore[operator]

        return self.filter(
            models.Q(parsed__isnull=True)
            | models.Q(
                models.Q(pub_date__isnull=True, parsed__lt=since)
                | models.Q(pub_date__isnull=False, pub_date__lt=since)
                | models.Q(parsed__lt=now - self.model.MAX_PARSER_FREQUENCY),
                parsed__lt=now - self.model.MIN_PARSER_FREQUENCY,
            )
        )

    def recommended(self, user: User) -> Self:
        """Returns recommended podcasts for user based on subscriptions. Includes `relevance` annotation."""

        # pick highest matches
        # we want the sum of the relevance of the recommendations, grouped by recommended

        subscribed = set(user.subscriptions.values_list("podcast", flat=True))
        recommended = set(user.recommended_podcasts.values_list("pk", flat=True))

        exclude = subscribed | recommended

        scores = (
            Recommendation.objects.filter(
                podcast__in=subscribed,
                recommended=models.OuterRef("pk"),
            )
            .exclude(recommended__in=exclude)
            .values("score")
            .order_by("-score")
        )

        return (
            self.alias(
                relevance=Coalesce(
                    models.Subquery(
                        scores.values("score")[:1],
                    ),
                    0,
                    output_field=models.DecimalField(),
                ),
            )
            .filter(models.Q(relevance__gt=0))
            .exclude(pk__in=exclude)
        )


class Podcast(models.Model):
    """Podcast channel or feed."""

    DEFAULT_PARSER_FREQUENCY: Final = timedelta(hours=24)
    MIN_PARSER_FREQUENCY: Final = timedelta(hours=1)
    MAX_PARSER_FREQUENCY: Final = timedelta(days=3)

    class ParserResult(models.TextChoices):
        SUCCESS = "success", "Success"
        DISCONTINUED = "discontinued", "Discontinued"
        DUPLICATE = "duplicate", "Duplicate"
        INVALID_DATA = "invalid_data", "Invalid Data"
        INVALID_RSS = "invalid_rss", "Invalid RSS"
        NOT_MODIFIED = "not_modified", "Not Modified"
        UNAVAILABLE = "unavailable", "Unavailable"

    class PodcastType(models.TextChoices):
        EPISODIC = "episodic", "Episodic"
        SERIAL = "serial", "Serial"

    rss = URLField(unique=True)

    active = models.BooleanField(
        default=True,
        help_text="Inactive podcasts will no longer be updated from their RSS feeds.",
    )

    canonical = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="duplicates",
    )

    private = models.BooleanField(
        default=False,
        help_text="Only available to subscribers",
    )

    etag = models.TextField(blank=True)
    title = models.TextField(blank=True)

    pub_date = models.DateTimeField(null=True, blank=True)

    num_episodes = models.PositiveIntegerField(default=0)
    has_similar_podcasts = models.BooleanField(default=False)

    parsed = models.DateTimeField(null=True, blank=True)

    parser_result = models.CharField(
        max_length=30,
        choices=ParserResult.choices,
        blank=True,
    )

    frequency = models.DurationField(default=DEFAULT_PARSER_FREQUENCY)

    modified = models.DateTimeField(
        null=True,
        blank=True,
    )

    content_hash = models.CharField(max_length=64, blank=True)

    num_retries = models.PositiveSmallIntegerField(default=0)

    cover_url = URLField(blank=True)

    funding_url = URLField(blank=True)
    funding_text = models.TextField(blank=True)

    language = models.CharField(
        max_length=2,
        default="en",
        validators=[MinLengthValidator(2)],
    )

    description = models.TextField(blank=True)
    website = URLField(blank=True)
    keywords = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    owner = models.TextField(blank=True)

    promoted = models.BooleanField(default=False)

    podcast_type = models.CharField(
        max_length=10,
        choices=PodcastType.choices,
        default=PodcastType.EPISODIC,
    )

    created = models.DateTimeField(auto_now_add=True)

    updated = models.DateTimeField(auto_now=True)

    explicit = models.BooleanField(default=False)

    categories = models.ManyToManyField(
        "podcasts.Category",
        blank=True,
        related_name="podcasts",
    )

    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="recommended_podcasts",
    )

    search_vector = SearchVectorField(null=True, editable=False)
    owner_search_vector = SearchVectorField(null=True, editable=False)

    objects: PodcastQuerySet = PodcastQuerySet.as_manager()  # type: ignore[assignment]

    if TYPE_CHECKING:
        episodes: EpisodeQuerySet
        subscriptions: models.Manager["Subscription"]
        recommendations: models.Manager["Recommendation"]
        similar: models.Manager["Recommendation"]

    class Meta:
        indexes: ClassVar[list] = [
            # Recent podcasts index
            models.Index(fields=["-pub_date"]),
            # Feed parser deduplication index
            models.Index(fields=["content_hash"]),
            # Discover feed index
            models.Index(fields=["promoted", "language", "-pub_date"]),
            # Feed parser scheduling index
            models.Index(
                fields=[
                    "active",
                    "-promoted",
                    "parsed",
                    "updated",
                ]
            ),
            # Common lookup index for public feeds
            models.Index(
                fields=["-pub_date"],
                condition=models.Q(
                    private=False,
                    pub_date__isnull=False,
                ),
                name="%(app_label)s_%(class)s_public_idx",
            ),
            # Search indexes
            GinIndex(fields=["search_vector"]),
            GinIndex(fields=["owner_search_vector"]),
        ]

    def __str__(self) -> str:
        """Returns podcast title or RSS if missing."""
        return self.title or self.rss

    def get_absolute_url(self) -> str:
        """Default absolute URL of podcast."""
        return self.get_detail_url()

    def get_detail_url(self) -> str:
        """Podcast detail URL"""
        return reverse(
            "podcasts:podcast_detail",
            kwargs={
                "podcast_id": self.pk,
                "slug": self.slug,
            },
        )

    def get_episodes_url(self) -> str:
        """Podcast episodes URL"""
        return reverse(
            "podcasts:episodes",
            kwargs={
                "podcast_id": self.pk,
                "slug": self.slug,
            },
        )

    def get_similar_url(self) -> str:
        """Podcast recommendations URL"""
        return reverse(
            "podcasts:similar",
            kwargs={
                "podcast_id": self.pk,
                "slug": self.slug,
            },
        )

    @cached_property
    def cleaned_title(self) -> str:
        """Strips HTML from title field."""
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self) -> str:
        """Strips HTML from description field."""
        return strip_html(self.description)

    @cached_property
    def cleaned_owner(self) -> str:
        """Strips HTML from owner field."""
        return strip_html(self.owner)

    @cached_property
    def slug(self) -> str:
        """Returns slugified title."""
        return slugify(self.title) or "podcast"

    @cached_property
    def seasons(self) -> list[Season]:
        """Returns list of seasons."""
        return [
            self.get_season(season)
            for season in self.episodes.filter(season__isnull=False)
            .values_list("season", flat=True)
            .order_by("season")
            .distinct()
        ]

    def get_season(self, season: int) -> Season:
        """Returns Season instance."""
        return Season(podcast=self, season=season)

    def get_next_scheduled_update(self) -> datetime:
        """Returns estimated next update:

        1. If parsed is NULL, should be ASAP.
        2. If pub date is NULL, add frequency to last parsed
        3. If pub date is not NULL, add frequency to pub date
        4. Scheduled time should always be in range of 1-24 hours.

        Note that this is a rough estimate: the precise update time depends
        on the frequency of the parse feeds cron and the number of other
        scheduled podcasts in the queue.
        """

        if self.parsed is None or self.frequency is None:
            return timezone.now()

        return min(
            self.parsed + self.MAX_PARSER_FREQUENCY,
            max(
                (self.pub_date or self.parsed) + self.frequency,
                self.parsed + self.MIN_PARSER_FREQUENCY,
            ),
        )

    def is_episodic(self) -> bool:
        """Returns true if podcast is episodic."""
        return self.podcast_type == self.PodcastType.EPISODIC

    def is_serial(self) -> bool:
        """Returns true if podcast is serial."""
        return self.podcast_type == self.PodcastType.SERIAL


class Subscription(models.Model):
    """Subscribed podcast belonging to a user's collection."""

    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_podcast",
                fields=["subscriber", "podcast"],
            )
        ]
        indexes: ClassVar[list] = [models.Index(fields=["-created"])]


class RecommendationQuerySet(models.QuerySet):
    """Custom QuerySet for Recommendation model."""

    def bulk_delete(self) -> int:
        """More efficient quick delete.

        Returns:
            number of rows deleted
        """
        return self._raw_delete(self.db)


class Recommendation(models.Model):
    """Recommendation based on similarity between two podcasts."""

    podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    recommended = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="similar",
    )

    score = models.DecimalField(
        decimal_places=10,
        max_digits=100,
        null=True,
        blank=True,
    )

    objects: RecommendationQuerySet = RecommendationQuerySet.as_manager()  # type: ignore[assignment]

    class Meta:
        indexes: ClassVar[list] = [
            models.Index(fields=["-score"]),
        ]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["podcast", "recommended"],
            ),
        ]
