from typing import ClassVar

from django.conf import settings
from django.db import models


class Subscription(models.Model):
    """Subscribed podcast belonging to a user's collection."""

    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    podcast = models.ForeignKey(
        "simplecasts.Podcast",
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
