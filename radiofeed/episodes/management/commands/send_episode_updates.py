from django.core.management import BaseCommand, CommandParser

from radiofeed.episodes import tasks
from radiofeed.users.notifications import get_recipients


class Command(BaseCommand):
    """Django management command to send episode updates to users."""

    help = "Send episode updates to users."

    def add_arguments(self, parser: CommandParser) -> None:
        """Parse command line arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            help="Max episodes in email.",
            default=6,
        )

    def handle(self, *, limit: int, **options) -> None:
        """Send episode updates to users."""
        for recipient_id in get_recipients().values_list("id", flat=True):
            tasks.send_episode_updates.enqueue(recipient_id=recipient_id, limit=limit)
