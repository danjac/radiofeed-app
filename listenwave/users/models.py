from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.db import models

if TYPE_CHECKING:
    from listenwave.episodes.models import AudioLogQuerySet, BookmarkQuerySet
    from listenwave.podcasts.models import PodcastQuerySet, Subscription


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
