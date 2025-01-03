from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from radiofeed.podcasts import emails
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Django management command."""

    help = "Send recommendation emails to users."

    def handle(self, *args, **options):
        """Handle implementation."""
        execute_thread_pool(
            emails.send_recommendations_email,
            self._get_email_addresses(),
        )

    def _get_email_addresses(self) -> QuerySet[EmailAddress]:
        # Return only active users with email notifications enabled

        return EmailAddress.objects.filter(
            verified=True,
            primary=True,
            user__is_active=True,
            user__send_email_notifications=True,
        ).select_related("user")