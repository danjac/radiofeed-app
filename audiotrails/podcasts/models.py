from __future__ import annotations

import dataclasses
import io
import mimetypes
import os
import uuid

from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, TrigramSimilarity
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.core.validators import MinLengthValidator, validate_image_file_extension
from django.db import models
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel
from PIL import Image
from PIL import ImageFile as PILImageFile
from PIL import UnidentifiedImageError
from PIL.Image import DecompressionBombError
from sorl.thumbnail import ImageField, get_thumbnail

from audiotrails.common.db import FastCountMixin, SearchMixin
from audiotrails.common.types import AnyUser, AuthenticatedUser
from audiotrails.podcasts.date_parser import parse_date
from audiotrails.podcasts.feed_parser import Feed, RssParserError, parse_feed
from audiotrails.podcasts.text_parser import extract_keywords

PILImageFile.LOAD_TRUNCATED_IMAGES = True
MAX_IMAGE_SIZE = 1000
THUMBNAIL_SIZE = 200

if TYPE_CHECKING:
    from audiotrails.episodes.models import Episode


@dataclasses.dataclass
class PlaceholderImage:
    width: int = THUMBNAIL_SIZE
    height: int = THUMBNAIL_SIZE

    @cached_property
    def url(self) -> str:
        # fetch lazy so we don't have issue finding staticfiles
        return static("img/podcast-icon.png")


_cover_image_placeholder = PlaceholderImage()


class CategoryQuerySet(models.QuerySet):
    def search(self, search_term: str, base_similarity: float = 0.2) -> models.QuerySet:
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
        return reverse("podcasts:category_detail", args=[self.pk, self.slug])


class PodcastQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    def with_follow_count(self) -> models.QuerySet:
        return self.annotate(follow_count=models.Count("follow"))


PodcastManager = models.Manager.from_queryset(PodcastQuerySet)


class Podcast(models.Model):

    rss: str = models.URLField(unique=True, max_length=500)
    etag: str = models.TextField(blank=True)
    title: str = models.TextField()
    pub_date: datetime = models.DateTimeField(null=True, blank=True)

    cover_image: ImageFile | None = ImageField(null=True, blank=True)
    cover_image_date: datetime = models.DateTimeField(null=True, blank=True)

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
    last_updated: datetime | None = models.DateTimeField(null=True, blank=True)

    explicit: bool = models.BooleanField(default=False)
    promoted: bool = models.BooleanField(default=False)

    categories: list[Category] = models.ManyToManyField(Category, blank=True)

    # received recommendation email
    recipients: list[AuthenticatedUser] = models.ManyToManyField(
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
        return reverse("podcasts:podcast_episodes", args=[self.pk, self.slug])

    def get_recommendations_url(self) -> str:
        return reverse("podcasts:podcast_recommendations", args=[self.pk, self.slug])

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
            f"podcast-episode-count-{self.pk}",
            self.get_episode_count,
            timeout=settings.DEFAULT_CACHE_TIMEOUT,
        )

    def get_opengraph_data(self, request: HttpRequest) -> dict[str, str | int]:

        og_data: dict[str, str | int] = {
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

    def get_cover_image_thumbnail(self) -> ImageFile | PlaceholderImage:
        """Returns cover image or placeholder. This is an expensive op,
        so use with caution."""

        if (
            self.cover_image
            and (
                img := get_thumbnail(
                    self.cover_image, str(THUMBNAIL_SIZE), format="WEBP", crop="center"
                )
            )
            and img.size is not None
        ):
            return img

        return _cover_image_placeholder

    def sync_rss_feed(self, force_update: bool = False) -> list[Episode]:
        try:
            headers = requests.head(self.rss, timeout=5).headers
            etag = headers.get("ETag", "")

            last_modified = parse_date(
                headers.get("Last-Modified", None)
            ) or parse_date(headers.get("Date", None))

            if not self.should_parse_rss_feed(
                etag, last_modified, force_update=force_update
            ):
                return []

            response = requests.get(self.rss, verify=True, stream=True, timeout=5)
            feed = parse_feed(response.content)

        except (RssParserError, requests.RequestException) as e:
            self.sync_error = str(e)
            self.num_retries += 1
            self.save()
            raise

        pub_date = feed.get_pub_date()

        if not self.should_sync_rss_feed(pub_date, force_update):
            return []

        now = timezone.now()

        # timestamps
        self.etag = etag
        self.pub_date = pub_date
        self.last_updated = now

        # description
        self.title = feed.title
        self.description = feed.description
        self.link = feed.link
        self.language = feed.language
        self.explicit = feed.explicit

        self.creators = feed.get_creators()

        # categories/keywords
        categories_dct = get_categories_dict()

        categories = [
            categories_dct[name] for name in feed.categories if name in categories_dct
        ]

        self.keywords = " ".join(
            name for name in feed.categories if name not in categories_dct
        )

        self.extracted_text = self.extract_keywords(feed, categories)

        self.categories.set(categories)  # type: ignore

        # reset errors
        self.sync_error = ""
        self.num_retries = 0

        # image
        if image := self.fetch_cover_image(feed.cover_url, force_update):
            self.cover_image = image
            self.cover_image_date = now

        self.save()

        return self.episode_set.sync_rss_feed(self, feed)

    def fetch_cover_image(self, url: str, force_update: bool) -> ImageFile | None:

        if not self.should_fetch_cover_image(url, force_update):
            return None

        try:
            response = requests.get(url, timeout=5, stream=True)
        except requests.RequestException:
            return None

        if (img := _create_image_obj(response.content)) is None:
            return None

        filename = _create_random_filename_from_response(response)

        image_file = ImageFile(img, name=filename)

        try:
            validate_image_file_extension(image_file)
        except ValidationError:
            return None

        return image_file

    def should_parse_rss_feed(
        self, etag: str, last_modified: datetime | None, force_update: bool
    ) -> bool:
        """Does preliminary check based on headers to determine whether to update this podcast.
        We also check the feed date info, but this is an optimization so we don't have to fetch and parse
        the RSS first."""
        return bool(
            force_update
            or self.pub_date is None
            or (etag and etag != self.etag)
            or (last_modified and last_modified > self.pub_date),
        )

    def should_sync_rss_feed(
        self, pub_date: datetime | None, force_update: bool
    ) -> bool:
        """Check if we should sync the RSS feed. This is called when we have already parsed the
        feed."""

        if pub_date is None:
            return False

        return any(
            (
                force_update,
                self.last_updated is None,
                self.last_updated and self.last_updated < pub_date,
            )
        )

    def should_fetch_cover_image(self, url: str, force_update: bool) -> bool:
        """Check if cover image should be updated."""
        if not url:
            return False

        if force_update or not self.cover_image or not self.cover_image_date:
            return True

        # conservative estimate: image generation/fetching is expensive so only
        # refetch if absolutely necessary

        try:
            headers = requests.head(url, timeout=5).headers
        except requests.RequestException:
            return False

        if (
            last_modified := parse_date(headers.get("Last-Modified", None))
        ) and last_modified > self.cover_image_date:
            return True

        # Date from CDNs tends to just be current timestamp, so ignore unless > 30 days old

        if (date := parse_date(headers.get("Date", None))) and (
            date - self.cover_image_date
        ).days > 30:

            return True

        return False

    def extract_keywords(self, feed: Feed, categories: list[Category]) -> str:
        """Extract keywords from text content for recommender"""
        text = " ".join(
            [
                self.title,
                self.description,
                self.keywords,
                self.creators,
            ]
            + [c.name for c in categories]
            + [item.title for item in feed.items][:6]
        )
        return " ".join(extract_keywords(self.language, text))


class Follow(TimeStampedModel):

    user: AuthenticatedUser = models.ForeignKey(
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

    def for_user(self, user: AuthenticatedUser) -> models.QuerySet:
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

    similarity: Decimal | None = models.DecimalField(
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


@lru_cache
def get_categories_dict() -> dict[str, Category]:
    return Category.objects.in_bulk(field_name="name")


def _create_random_filename_from_response(response: requests.Response) -> str:
    _, ext = os.path.splitext(urlparse(response.url).path)

    if ext is None:
        try:
            content_type = response.headers["Content-Type"].split(";")[0]
        except KeyError:
            content_type = mimetypes.guess_type(response.url)[0] or ""

        ext = mimetypes.guess_extension(content_type) or ""

    return uuid.uuid4().hex + ext


def _create_image_obj(raw: bytes) -> Image:
    try:
        img = Image.open(io.BytesIO(raw))

        if img.height > MAX_IMAGE_SIZE or img.width > MAX_IMAGE_SIZE:
            img = img.resize((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.ANTIALIAS)

        # remove Alpha channel
        img = img.convert("RGB")

        fp = io.BytesIO()
        img.seek(0)
        img.save(fp, "PNG")

        return fp

    except (
        DecompressionBombError,
        UnidentifiedImageError,
    ):
        return None
