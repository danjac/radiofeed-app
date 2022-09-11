from __future__ import annotations

from django.core.management.base import BaseCommand

from radiofeed.podcasts import emails
from radiofeed.users.models import User


class Command(BaseCommand):
    """Django command."""

    help = """Sends recommendations emails"""

    def handle(self, *args, **options):
        """Command handler implementation."""
        for user in User.objects.email_notification_recipients():
            emails.send_recommendations_email(user)
