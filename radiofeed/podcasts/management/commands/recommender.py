from __future__ import annotations

import multiprocessing

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

    def _send_recommendations_emails(self):
        with multiprocessing.pool.ThreadPool(
            processes=multiprocessing.cpu_count()
        ) as pool:
            pool.map(
                send_recommendations_email,
                User.objects.email_notification_recipients(),
            )
