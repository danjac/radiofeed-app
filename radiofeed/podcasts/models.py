# Django
from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

# Third Party Libraries
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField


class CategoryQuerySet(models.QuerySet):
    def search(self, search_term, base_similarity=0.2):
        return self.annotate(similarity=TrigramSimilarity("name", search_term)).filter(
            similarity__gte=base_similarity
        )


class CategoryManager(models.Manager.from_queryset(CategoryQuerySet)):
    ...


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
        return reverse("podcasts:category_detail", args=[self.id, self.slug])


class PodcastQuerySet(models.QuerySet):
    def search(self, search_term, base_similarity=0.2):
        return self.annotate(similarity=TrigramSimilarity("title", search_term)).filter(
            similarity__gte=base_similarity
        )


class PodcastManager(models.Manager.from_queryset(PodcastQuerySet)):
    ...


class Podcast(models.Model):

    rss = models.URLField(unique=True, max_length=500)
    etag = models.TextField(blank=True)
    title = models.TextField()
    pub_date = models.DateTimeField(null=True, blank=True)

    cover_image = ImageField(null=True, blank=True)

    itunes = models.URLField(max_length=500, null=True, blank=True)

    language = models.CharField(max_length=2, default="en")
    description = models.TextField(blank=True)
    link = models.URLField(null=True, blank=True, max_length=500)
    keywords = models.TextField(blank=True)

    authors = models.TextField(blank=True)

    last_updated = models.DateTimeField(null=True, blank=True)

    explicit = models.BooleanField(default=False)

    categories = models.ManyToManyField(Category, blank=True)

    objects = PodcastManager()

    class Meta:
        indexes = [
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["title"]),
            models.Index(fields=["-title"]),
        ]

    def __str__(self):
        return self.title or self.rss

    def get_absolute_url(self):
        return reverse("podcasts:podcast_detail", args=[self.id, self.slug])

    @property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "podcast"


class Subscription(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="uniq_subscription", fields=["user", "podcast"]
            )
        ]
        indexes = [models.Index(fields=["-created"])]
