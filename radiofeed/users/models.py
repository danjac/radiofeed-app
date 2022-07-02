from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    def email_notification_recipients(self):
        """Returns all active users who have enabled email notifications in their settings.

        Returns:
            QuerySet
        """
        return self.filter(is_active=True, send_email_notifications=True)

    def for_email(self, email):
        """Returns users matching this email address, including both
        primary and secondary email addresses
        Returns:
            QuerySet
        """
        return self.filter(
            models.Q(emailaddress__email__iexact=email) | models.Q(email__iexact=email)
        )


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    def create_user(self, username, email, password=None, **kwargs):
        """Create new user

        Args:
            username (str)
            email (str)
            password (str | None): if None sets unusable password
            **kwargs: any other User fields

        Returns:
            User: saved User instance
        """
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **kwargs,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **kwargs):
        """Create new superuser

        Args:
            username (str)
            email (str)
            password (str)
            **kwargs: any other User fields

        Returns:
            User: saved User instance
        """
        return self.create_user(
            username,
            email,
            password,
            is_staff=True,
            is_superuser=True,
            **kwargs,
        )


class User(AbstractUser):
    send_email_notifications = models.BooleanField(default=True)

    objects = UserManager()

    def get_email_addresses(self):
        """Get set of all emails belonging to user.

        Returns:
            set[str]: set of email addresses
        """
        return {self.email} | set(self.emailaddress_set.values_list("email", flat=True))
