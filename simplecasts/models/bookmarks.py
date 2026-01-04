from typing import ClassVar

from django.conf import settings
from django.db import models


class Bookmark(models.Model):
    """Bookmarked episodes."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    episode = models.ForeignKey(
        "simplecasts.Episode",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_episode",
                fields=["user", "episode"],
            )
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["user", "episode"]),
            models.Index(
                fields=["user", "created"],
                include=["episode_id"],
                name="%(app_label)s_%(class)s_desc_idx",
            ),
            models.Index(
                fields=["user", "-created"],
                include=["episode_id"],
                name="%(app_label)s_%(class)s_asc_idx",
            ),
        ]
