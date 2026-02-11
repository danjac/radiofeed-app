from django.core.management.base import BaseCommand, CommandParser

from radiofeed.podcasts.tasks import send_podcast_recommendations
from radiofeed.users.notifications import get_recipients


class Command(BaseCommand):
    """Send podcast recommendations to users."""

    help = "Send podcast recommendations to users"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=6,
            help="Number of podcasts to recommend per user",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Handler implementation."""

        recipient_ids = get_recipients().values_list("id", flat=True)
        for recipient_id in recipient_ids:
            send_podcast_recommendations.enqueue(recipient_id=recipient_id, limit=limit)
