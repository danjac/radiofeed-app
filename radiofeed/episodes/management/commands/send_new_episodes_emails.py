from __future__ import annotations

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand

from radiofeed.episodes.tasks import send_new_episodes_email
from radiofeed.users.models import User


class Command(BaseCommand):
    help = """
    Send new episodes notification emails
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--interval", help="Interval between sending emails (days)", default=7
        )

    def handle(self, *args, **options) -> None:
        interval = timedelta(days=options["interval"])
        for user_id in User.objects.email_notification_recipients().values_list(
            "pk", flat=True
        ):
            send_new_episodes_email(user_id, interval=interval)
