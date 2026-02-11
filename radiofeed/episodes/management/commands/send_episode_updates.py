from django.core.management.base import BaseCommand, CommandParser

from radiofeed.episodes.tasks import send_episode_updates
from radiofeed.users.notifications import get_recipients


class Command(BaseCommand):
    """Send notifications to users about new podcast episodes."""

    help = "Send notifications to users about new podcast episodes"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--days-since",
            "-d",
            type=int,
            default=7,
            help="Number of days to look back for new episodes",
        )
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=6,
            help="Number of new podcast episodes to notify per user",
        )

    def handle(self, *, days_since: int, limit: int, **options) -> None:
        """Handler implementation."""

        recipient_ids = get_recipients().values_list("id", flat=True)

        for recipient_id in recipient_ids:
            send_episode_updates.enqueue(
                recipient_id=recipient_id,
                days_since=days_since,
                limit=limit,
            )
