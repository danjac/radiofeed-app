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
                emails.send_recommendations_email,
                User.objects.filter(
                    is_active=True,
                    send_email_notifications=True,
                ),
            )
