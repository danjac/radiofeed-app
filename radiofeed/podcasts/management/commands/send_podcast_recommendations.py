from django.core.management import BaseCommand, CommandParser

from radiofeed.podcasts import tasks
from radiofeed.users.notifications import get_recipients


class Command(BaseCommand):
    """Django management command to send podcast recommendations to users."""

    help = "Send podcast recommendations to users."

    def add_arguments(self, parser: CommandParser) -> None:
        """Parse command line arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=6,
            help="Max recommendations in email.",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Send podcast recommendations to users."""
        for recipient_id in get_recipients().values_list("id", flat=True):
            tasks.send_podcast_recommendations.enqueue(
                recipient_id=recipient_id, limit=limit
            )
