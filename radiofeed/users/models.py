from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model."""

    send_email_notifications = models.BooleanField(default=True)
