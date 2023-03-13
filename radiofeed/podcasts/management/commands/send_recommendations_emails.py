from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from radiofeed.podcasts import emails
from radiofeed.users.models import User


class Command(BaseCommand):
    """Django command."""

    help = """Sends recommendations emails"""

    def handle(self, **options):
        """Command handler implementation."""
        with ThreadPoolExecutor() as executor:
            executor.map(
                emails.send_recommendations_email,
                User.objects.email_notification_recipients(),
            )
