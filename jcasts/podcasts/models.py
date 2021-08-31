from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, TrigramSimilarity
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from jcasts.shared.cleaners import strip_html
from jcasts.shared.db import FastCountMixin, SearchMixin


class CategoryQuerySet(models.QuerySet):
    def search(self, search_term, base_similarity=0.2):
        return self.annotate(
            similarity=TrigramSimilarity("name", force_str(search_term))
        ).filter(similarity__gte=base_similarity)


CategoryManager = models.Manager.from_queryset(CategoryQuerySet)


class Category(models.Model):

    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
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

    def __str__(self):
        return self.name

    @property
    def slug(self):
        return slugify(self.name, allow_unicode=False)

    def get_absolute_url(self):
        return reverse("podcasts:category_detail", args=[self.pk, self.slug])


class PodcastQuerySet(FastCountMixin, SearchMixin, models.QuerySet):
    def active(self):
        return self.filter(active=True, pub_date__isnull=False)

    def frequent(self):
        return self.active().filter(
            pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD,
        )


PodcastManager = models.Manager.from_queryset(PodcastQuerySet)


class Podcast(models.Model):

    rss = models.URLField(unique=True, max_length=500)
    active = models.BooleanField(default=True)

    etag = models.TextField(blank=True)
    title = models.TextField()

    pub_date = models.DateTimeField(null=True, blank=True)
    scheduled = models.DateTimeField(null=True, blank=True)
    parsed = models.DateTimeField(null=True, blank=True)
    queued = models.DateTimeField(null=True, blank=True)

    http_status = models.SmallIntegerField(null=True, blank=True)
    exception = models.TextField(blank=True)

    num_episodes = models.PositiveIntegerField(default=0)

    cover_url = models.URLField(max_length=2083, null=True, blank=True)

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

    modified = models.DateTimeField(null=True, blank=True)

    explicit = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)

    categories = models.ManyToManyField(Category, blank=True)

    # received recommendation email
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="recommended_podcasts"
    )

    search_vector = SearchVectorField(null=True, editable=False)

    objects = PodcastManager()

    class Meta:
        indexes = [
            models.Index(fields=["scheduled", "-pub_date"]),
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self):
        return self.title or self.rss

    def get_absolute_url(self):
        return self.get_detail_url()

    @cached_property
    def cleaned_title(self):
        return strip_html(self.title)

    @cached_property
    def cleaned_description(self):
        return strip_html(self.description)

    def get_latest_url(self):
        return reverse("podcasts:latest", args=[self.pk])

    def get_detail_url(self):
        return reverse("podcasts:podcast_detail", args=[self.pk, self.slug])

    def get_episodes_url(self):
        return reverse("podcasts:podcast_episodes", args=[self.pk, self.slug])

    def get_recommendations_url(self):
        return reverse("podcasts:podcast_recommendations", args=[self.pk, self.slug])

    def get_domain(self):
        return urlparse(self.rss).netloc.rsplit("www.", 1)[-1]

    @property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "podcast"

    def is_following(self, user):
        if user.is_anonymous:
            return False
        return Follow.objects.filter(podcast=self, user=user).exists()

    def get_opengraph_data(self, request):

        og_data: dict[str, str | int] = {
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


class Follow(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["user", "podcast"],
            )
        ]
        indexes = [models.Index(fields=["-created"])]


class RecommendationQuerySet(models.QuerySet):
    def bulk_delete(self):
        """More efficient quick delete"""
        return self._raw_delete(self.db)

    def for_user(self, user):
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

    podcast = models.ForeignKey(Podcast, related_name="+", on_delete=models.CASCADE)
    recommended = models.ForeignKey(Podcast, related_name="+", on_delete=models.CASCADE)

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
