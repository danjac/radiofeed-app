from django.core.management.base import BaseCommand

from radiofeed.podcasts import emails
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor
from radiofeed.users.models import User


class Command(BaseCommand):
    """BaseCommand subclass."""

    help = "Send recommendation emails to subscribers."

    def handle(self, *args, **options) -> None:
        """Implementation of command."""

        with DatabaseSafeThreadPoolExecutor() as executor:
            executor.db_safe_map(
                emails.send_recommendations_email,
                User.objects.filter(
                    is_active=True,
                    send_email_notifications=True,
                ),
            )
