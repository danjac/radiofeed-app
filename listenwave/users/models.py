from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model."""

    send_email_notifications = models.BooleanField(default=True)

    @property
    def name(self):
        """Return the user's first name or username."""
        return self.first_name or self.username
