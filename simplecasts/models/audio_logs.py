from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from simplecasts.models.search import SearchQuerySetMixin


class AudioLogQuerySet(SearchQuerySetMixin, models.QuerySet):
    """Custom queryset for Bookmark model."""

    default_search_fields = (
        "episode__search_vector",
        "episode__podcast__search_vector",
    )


class AudioLog(models.Model):
    """Record of user listening history."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audio_logs",
    )
    episode = models.ForeignKey(
        "simplecasts.Episode",
        on_delete=models.CASCADE,
        related_name="audio_logs",
    )

    listened = models.DateTimeField()
    current_time = models.PositiveIntegerField(default=0)
    duration = models.PositiveIntegerField(default=0)

    objects: AudioLogQuerySet = AudioLogQuerySet.as_manager()  # type: ignore[assignment]

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_user_episode",
                fields=["user", "episode"],
            ),
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["user", "episode"]),
            models.Index(
                fields=["user", "listened"],
                include=["episode_id"],
                name="%(app_label)s_%(class)s_desc_idx",
            ),
            models.Index(
                fields=["user", "-listened"],
                include=["episode_id"],
                name="%(app_label)s_%(class)s_asc_idx",
            ),
        ]

    @cached_property
    def percent_complete(self) -> int:
        """Returns percentage of episode listened to."""
        if 0 in (self.current_time, self.duration):
            return 0

        return min(100, round((self.current_time / self.duration) * 100))
