from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, TrigramSimilarity
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from radiofeed.common.db import FastCountMixin, SearchMixin
from radiofeed.common.html import strip_html


class CategoryQuerySet(models.QuerySet):
    def search(self, search_term, base_similarity=0.2):
        return self.annotate(
            similarity=TrigramSimilarity("name", force_str(search_term))
        ).filter(similarity__gte=base_similarity)


class Category(models.Model):

    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def slug(self):
        return slugify(self.name, allow_unicode=False)

    def get_absolute_url(self):
        return reverse("podcasts:category_detail", args=[self.pk, self.slug])


class PodcastQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    ...


PodcastManager = models.Manager.from_queryset(PodcastQuerySet)


class Podcast(models.Model):
    rss = models.URLField(unique=True, max_length=500)
    active = models.BooleanField(default=True)

    etag = models.TextField(blank=True)
    title = models.TextField()

    # latest episode pub date from RSS feed
    pub_date = models.DateTimeField(null=True, blank=True)

    # last parse time (success or fail)
    parsed = models.DateTimeField(null=True, blank=True)

    # Last-Modified header from RSS feed
    modified = models.DateTimeField(null=True, blank=True)

    # hash of last polled content
    content_hash = models.CharField(max_length=64, null=True, blank=True)

    http_status = models.SmallIntegerField(null=True, blank=True)

    cover_url = models.URLField(max_length=2083, null=True, blank=True)

    funding_url = models.URLField(max_length=2083, null=True, blank=True)
    funding_text = models.TextField(blank=True)

    language = models.CharField(
        max_length=2, default="en", validators=[MinLengthValidator(2)]
    )
    description = models.TextField(blank=True)
    link = models.URLField(max_length=2083, null=True, blank=True)
    keywords = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    owner = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    explicit = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)

    categories = models.ManyToManyField("podcasts.Category", blank=True)

    # received recommendation email
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="recommended_podcasts",
    )

    search_vector = SearchVectorField(null=True, editable=False)

    objects = PodcastManager()

    class Meta:
        indexes = [
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["promoted"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self):
        return self.title or self.rss

    def get_absolute_url(self):
        return self.get_detail_url()

    def get_detail_url(self):
        return reverse("podcasts:podcast_detail", args=[self.pk, self.slug])

    def get_episodes_url(self):
        return reverse("podcasts:podcast_episodes", args=[self.pk, self.slug])

    def get_similar_url(self):
        return reverse("podcasts:podcast_similar", args=[self.pk, self.slug])

    def get_latest_episode_url(self):
        return reverse("podcasts:latest_episode", args=[self.pk, self.slug])

    @cached_property
    def cleaned_title(self):
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self):
        return strip_html(self.description)

    @cached_property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "no-title"

    def is_subscribed(self, user):
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(podcast=self, user=user).exists()

    def get_subscribe_target(self):
        return f"subscribe-buttons-{self.id}"


class Subscription(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    podcast = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_podcast",
                fields=["user", "podcast"],
            )
        ]
        indexes = [models.Index(fields=["-created"])]


class RecommendationQuerySet(models.QuerySet):
    def bulk_delete(self):
        """More efficient quick delete"""
        return self._raw_delete(self.db)


RecommendationManager = models.Manager.from_queryset(RecommendationQuerySet)


class Recommendation(models.Model):

    podcast = models.ForeignKey(
        "podcasts.Podcast",
        related_name="+",
        on_delete=models.CASCADE,
    )

    recommended = models.ForeignKey(
        "podcasts.Podcast",
        related_name="+",
        on_delete=models.CASCADE,
    )

    frequency = models.PositiveIntegerField(default=0)

    similarity = models.DecimalField(
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
