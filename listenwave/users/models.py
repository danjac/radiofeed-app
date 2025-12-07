from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.db import models

if TYPE_CHECKING:
    from listenwave.episodes.models import AudioLog, Bookmark
    from listenwave.podcasts.models import PodcastQuerySet, Subscription


class User(AbstractUser):
    """Custom User model."""

    send_email_notifications = models.BooleanField(default=True)

    if TYPE_CHECKING:
        audio_logs: models.Manager[AudioLog]
        bookmarks: models.Manager[Bookmark]
        subscriptions: models.Manager[Subscription]
        recommended_podcasts: PodcastQuerySet

    @property
    def name(self):
        """Return the user's first name or username."""
        return self.first_name or self.username
