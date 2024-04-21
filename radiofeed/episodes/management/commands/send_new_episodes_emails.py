import functools
from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand

from radiofeed.episodes import emails
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor
from radiofeed.users.models import User


class Command(BaseCommand):
    """Command to send recommendations emails."""

    help = """Sends recommendations emails"""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""

        parser.add_argument(
            "--num_episodes",
            help="Max number of episodes per email.",
            type=int,
            default=12,
        )

        parser.add_argument(
            "--since",
            help="Episodes published since n hours ago.",
            type=int,
            default=24,
        )

    def handle(self, **options):
        """Command handler implementation."""

        send_new_episodes_email = functools.partial(
            emails.send_new_episodes_email,
            num_episodes=options["num_episodes"],
            since=timedelta(hours=options["since"]),
        )

        with DatabaseSafeThreadPoolExecutor() as executor:
            (
                executor.db_safe_map(
                    send_new_episodes_email,
                    User.objects.filter(
                        is_active=True,
                        send_email_notifications=True,
                    ),
                ),
            )
