from django.core.management.base import BaseCommand

from radiofeed.futures import DatabaseSafeThreadPoolExecutor
from radiofeed.podcasts import emails
from radiofeed.users.models import User


class Command(BaseCommand):
    """Command to send recommendations emails."""

    help = """Sends recommendations emails"""

    def handle(self, **options):
        """Command handler implementation."""

        with DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(
                self._send_recommendations_email,
                User.objects.email_notification_recipients().values_list(
                    "pk", flat=True
                ),
            )

    def _send_recommendations_email(self, user_id: int) -> None:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
