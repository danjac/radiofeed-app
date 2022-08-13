from __future__ import annotations

from django.core.management.base import BaseCommand

from radiofeed.podcasts import recommender
from radiofeed.podcasts.emails import send_recommendations_email
from radiofeed.users.models import User


class Command(BaseCommand):
    """Django command."""

    help = """
    Runs recommendation algorithms.
    """

    def add_arguments(self, parser):
        """Parse command args."""
        parser.add_argument(
            "--email",
            help="Send recommendations emails to users",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options):
        """Command handler implementation."""
        if options["email"]:
            self._send_recommendations_emails()
        else:
            recommender.recommend()

    def send_recommendations_emails(self):
        for user in User.objects.email_notification_recipients():
            send_recommendations_email(user)
