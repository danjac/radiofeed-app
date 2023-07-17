from __future__ import annotations

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    """Custom QuerySet for User model."""

    def email_notification_recipients(self) -> models.QuerySet[User]:
        """Returns all active users who have enabled email notifications in their
        settings."""
        return self.filter(is_active=True, send_email_notifications=True)

    def for_email(self, email: str) -> models.QuerySet[User]:
        """Returns users matching this email address, including both primary and
        secondary email addresses."""
        return self.filter(
            models.Q(emailaddress__email__iexact=email) | models.Q(email__iexact=email)
        )


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):  # type: ignore
    """Custom Manager for User model."""

    def create_user(
        self,
        username: str,
        email: str,
        password: str | None = None,
        **kwargs,
    ) -> User:
        """Create new user."""
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **kwargs,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        username: str,
        email: str,
        password: str | None = None,
        **kwargs,
    ) -> User:
        """Create new superuser."""
        return self.create_user(
            username,
            email,
            password,
            is_staff=True,
            is_superuser=True,
            **kwargs,
        )


class User(AbstractUser):
    """Custom User model."""

    send_email_notifications: bool = models.BooleanField(default=True)

    objects: models.Manager[User] = UserManager()

    def get_email_addresses(self) -> set[str]:
        """Get set of all emails belonging to user."""
        return {self.email} | set(self.emailaddress_set.values_list("email", flat=True))
