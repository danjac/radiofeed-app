from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand

from radiofeed.podcasts import emails
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Django management command."""

    help = "Send recommendation emails to users."

    def handle(self, **options):
        """Handle implementation."""
        execute_thread_pool(
            emails.send_recommendations_email,
            EmailAddress.objects.filter(
                user__is_active=True,
                user__send_email_notifications=True,
                primary=True,
                verified=True,
            ),
        )
