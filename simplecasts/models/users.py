from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.db import models

if TYPE_CHECKING:
    from simplecasts.models.audio_logs import AudioLogQuerySet
    from simplecasts.models.bookmarks import BookmarkQuerySet
    from simplecasts.models.podcasts import PodcastQuerySet
    from simplecasts.models.subscriptions import Subscription


class User(AbstractUser):
    """Custom User model."""

    send_email_notifications = models.BooleanField(default=True)

    if TYPE_CHECKING:
        audio_logs: AudioLogQuerySet
        bookmarks: BookmarkQuerySet
        recommended_podcasts: PodcastQuerySet
        subscriptions: models.Manager[Subscription]

    @property
    def name(self):
        """Return the user's first name or username."""
        return self.first_name or self.username
