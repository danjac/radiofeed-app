from typing import TYPE_CHECKING

from django.db import models
from django.urls import reverse
from slugify import slugify

if TYPE_CHECKING:
    from simplecasts.models.podcasts import PodcastQuerySet


class Category(models.Model):
    """iTunes category."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    itunes_genre_id = models.PositiveIntegerField(null=True, blank=True)

    if TYPE_CHECKING:
        podcasts: "PodcastQuerySet"

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self) -> str:
        """Returns category name."""
        return self.name

    def save(self, **kwargs) -> None:
        """Overrides save to auto-generate slug."""
        self.slug = slugify(self.name, allow_unicode=False)
        super().save(**kwargs)

    def get_absolute_url(self) -> str:
        """Absolute URL to a category."""
        return reverse("categories:detail", kwargs={"slug": self.slug})
