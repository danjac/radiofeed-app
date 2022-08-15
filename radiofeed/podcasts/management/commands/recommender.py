from __future__ import annotations

from django.core.management.base import BaseCommand

from radiofeed.podcasts import emails, recommender
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

            for user in User.objects.email_notification_recipients():
                emails.send_recommendations_email(user)

        else:
            recommender.recommend()
