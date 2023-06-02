from django.core.management.base import BaseCommand

from radiofeed import futures
from radiofeed.podcasts import emails
from radiofeed.users.models import User


class Command(BaseCommand):
    """Command to send recommendations emails."""

    help = """Sends recommendations emails"""

    def handle(self, **options):
        """Command handler implementation."""
        futures.safemap(
            User.objects.email_notification_recipients().values_list("pk", flat=True),
            self._send_recommendations_email,
        )

    def _send_recommendations_email(self, user_id: int) -> None:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
