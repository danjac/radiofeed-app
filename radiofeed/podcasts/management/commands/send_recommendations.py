from django.core.management.base import BaseCommand
from django.db.models import F, QuerySet

from radiofeed.podcasts import emails
from radiofeed.thread_pool import execute_thread_pool
from radiofeed.users.models import User


class Command(BaseCommand):
    """Django management command."""

    help = "Send recommendation emails to users."

    def handle(self, *args, **options):
        """Handle implementation."""
        execute_thread_pool(
            emails.send_recommendations_email,
            self._get_recipients(),
        )

    def _get_recipients(self) -> QuerySet[User]:
        # Return only active users with email notifications enabled

        return User.objects.filter(
            is_active=True,
            send_email_notifications=True,
            emailaddress__primary=True,
            emailaddress__verified=True,
            emailaddress__email=F("email"),
        )
