from typing import ClassVar

from django.db import models


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
        "simplecasts.Podcast",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    recommended = models.ForeignKey(
        "simplecasts.Podcast",
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
