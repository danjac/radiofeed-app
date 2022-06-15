from __future__ import annotations

from argparse import ArgumentParser

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

    def handle(self, *args, **kwargs) -> None:
        send_new_episodes_email.map(
            User.objects.email_notification_recipients().values_list("pk", flat=True)
        )
