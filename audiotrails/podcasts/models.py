from __future__ import annotations

import dataclasses
import decimal

from datetime import datetime
from typing import Dict, List, Optional, Protocol, Union

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVectorField,
    TrigramSimilarity,
)
from django.core.cache import cache
from django.core.validators import MinLengthValidator
from django.db import models
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel
from PIL import ImageFile
from sorl.thumbnail import ImageField, get_thumbnail

from audiotrails.shared.db import FastCountMixin
from audiotrails.shared.types import AnyUser

ImageFile.LOAD_TRUNCATED_IMAGES = True

THUMBNAIL_SIZE = 200


class CoverImage(Protocol):
    width: int
    height: int
    url: str


@dataclasses.dataclass
class PlaceholderImage:
    width: int
    height: int

    @cached_property
    def url(self) -> str:
        # fetch lazy so we don't have issue finding staticfiles
        return static("img/podcast-icon.png")


_cover_image_placeholder = PlaceholderImage(width=THUMBNAIL_SIZE, height=THUMBNAIL_SIZE)


class CategoryQuerySet(models.QuerySet):
    def search(self, search_term: int, base_similarity: float = 0.2) -> models.QuerySet:
        return self.annotate(
            similarity=TrigramSimilarity("name", force_str(search_term))
        ).filter(similarity__gte=base_similarity)


CategoryManager = models.Manager.from_queryset(CategoryQuerySet)


class Category(models.Model):

    name: str = models.CharField(max_length=100, unique=True)
    parent: Category = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    # https://itunes.apple.com/search?term=podcast&genreId=1402&limit=20
    itunes_genre_id: int = models.IntegerField(
        verbose_name="iTunes Genre ID", null=True, blank=True, unique=True
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
        return reverse("podcasts:category_detail", args=[self.id, self.slug])


class PodcastQuerySet(FastCountMixin, models.QuerySet):
    def search(self, search_term: str) -> models.QuerySet:
        if not search_term:
            return self.none()

        query = SearchQuery(force_str(search_term), search_type="websearch")
        return self.annotate(
            rank=SearchRank(models.F("search_vector"), query=query)
        ).filter(search_vector=query)

    def with_follow_count(self) -> models.QuerySet:
        return self.annotate(follow_count=models.Count("follow"))


PodcastManager = models.Manager.from_queryset(PodcastQuerySet)


class Podcast(models.Model):

    rss: str = models.URLField(unique=True, max_length=500)
    etag: str = models.TextField(blank=True)
    title: str = models.TextField()
    pub_date: Optional[datetime] = models.DateTimeField(null=True, blank=True)

    cover_image: Optional[CoverImage] = ImageField(null=True, blank=True)

    itunes: str = models.URLField(max_length=500, null=True, blank=True, unique=True)

    language: str = models.CharField(
        max_length=2, default="en", validators=[MinLengthValidator(2)]
    )
    description: str = models.TextField(blank=True)
    link: str = models.URLField(null=True, blank=True, max_length=500)
    keywords: str = models.TextField(blank=True)
    extracted_text: str = models.TextField(blank=True)
    creators: str = models.TextField(blank=True)

    created: datetime = models.DateTimeField(auto_now_add=True)
    last_updated: Optional[datetime] = models.DateTimeField(null=True, blank=True)

    explicit: bool = models.BooleanField(default=False)
    promoted: bool = models.BooleanField(default=False)

    categories: List[Category] = models.ManyToManyField(Category, blank=True)

    # received recommendation email
    recipients: List[settings.AUTH_USER_MODEL] = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="recommended_podcasts"
    )

    sync_error: str = models.TextField(blank=True)
    num_retries: int = models.PositiveIntegerField(default=0)

    search_vector: str = SearchVectorField(null=True, editable=False)

    objects = PodcastManager()

    class Meta:
        indexes = [
            models.Index(fields=["-created", "-pub_date"]),
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self) -> str:
        return self.title or self.rss

    def get_absolute_url(self) -> str:
        return self.get_episodes_url()

    def get_episodes_url(self) -> str:
        return reverse("podcasts:podcast_episodes", args=[self.id, self.slug])

    def get_recommendations_url(self) -> str:
        return reverse("podcasts:podcast_recommendations", args=[self.id, self.slug])

    @property
    def slug(self) -> str:
        return slugify(self.title, allow_unicode=False) or "podcast"

    def is_following(self, user: AnyUser) -> bool:
        if user.is_anonymous:
            return False
        return Follow.objects.filter(podcast=self, user=user).exists()

    def get_episode_count(self) -> int:
        return self.episode_set.distinct().count()

    def get_cached_episode_count(self) -> int:
        return cache.get_or_set(
            f"podcast-episode-count-{self.id}",
            self.get_episode_count,
            timeout=settings.DEFAULT_CACHE_TIMEOUT,
        )

    def get_opengraph_data(self, request: HttpRequest) -> Dict[str, Union[str, int]]:

        og_data: Dict[str, Union[str, int]] = {
            "url": request.build_absolute_uri(self.get_absolute_url()),
            "title": f"{request.site.name} | {self.title}",
            "description": self.description,
            "keywords": self.keywords,
        }

        if self.cover_image:
            og_data = {
                **og_data,
                "image": self.cover_image.url,
                "image_height": self.cover_image.height,
                "image_width": self.cover_image.width,
            }
        return og_data

    def get_cover_image_thumbnail(self) -> Union[CoverImage, PlaceholderImage]:
        """Returns cover image or placeholder. This is an expensive op,
        so use with caution."""

        if self.cover_image:
            if (
                img := get_thumbnail(
                    self.cover_image, str(THUMBNAIL_SIZE), format="WEBP", crop="center"
                )
            ) and img.size is not None:
                return img

        return _cover_image_placeholder


class Follow(TimeStampedModel):

    user: settings.AUTH_USER_MODEL = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    podcast: Podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(name="uniq_follow", fields=["user", "podcast"])
        ]
        indexes = [models.Index(fields=["-created"])]


class RecommendationQuerySet(models.QuerySet):
    def bulk_delete(self) -> int:
        """More efficient quick delete"""
        return self._raw_delete(self.db)

    def with_followed(self, user: AnyUser) -> models.QuerySet:
        """Marks which recommendations are followed by this user."""
        if user.is_anonymous:
            return self.annotate(
                is_followed=models.Value(False, output_field=models.BooleanField())
            )
        return self.annotate(
            is_followed=models.Exists(
                Follow.objects.filter(user=user, podcast=models.OuterRef("recommended"))
            )
        )

    def for_user(self, user: settings.AUTH_USER_MODEL) -> models.QuerySet:
        podcast_ids = (
            set(
                user.favorite_set.select_related("episode__podcast").values_list(
                    "episode__podcast", flat=True
                )
            )
            | set(
                user.queueitem_set.select_related("episode__podcast").values_list(
                    "episode__podcast", flat=True
                )
            )
            | set(
                user.audiolog_set.select_related("episode__podcast").values_list(
                    "episode__podcast", flat=True
                )
            )
            | set(user.follow_set.values_list("podcast", flat=True))
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

    similarity: decimal.Decimal = models.DecimalField(
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
                fields=["podcast", "recommended"], name="unique_recommendation"
            ),
        ]
