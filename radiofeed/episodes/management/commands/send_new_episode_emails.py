from django.core.management.base import BaseCommand

from radiofeed.episodes import emails
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor
from radiofeed.users.models import User


class Command(BaseCommand):
    """Command to send recommendations emails."""

    help = """Sends recommendations emails"""

    def handle(self, **options):
        """Command handler implementation."""

        with DatabaseSafeThreadPoolExecutor() as executor:
            (
                executor.db_safe_map(
                    emails.send_new_episodes_email,
                    User.objects.filter(
                        is_active=True,
                        send_email_notifications=True,
                    ),
                ),
            )
