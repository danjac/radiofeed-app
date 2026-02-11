from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Case, Count, IntegerField, When

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import parse_podcast_feed


class Command(BaseCommand):
    """Parse feeds for all active podcasts."""

    help = "Parse feeds for all active podcasts."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=360,
            help="Number of podcasts to parse",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Handle the command execution."""

        podcast_ids = (
            Podcast.objects.annotate(
                subscribers=Count("subscriptions"),
                is_new=Case(
                    When(parsed__isnull=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .scheduled()
            .filter(active=True)
            .order_by(
                "-is_new",
                "-subscribers",
                "-promoted",
                "parsed",
                "updated",
            )
        ).values_list("pk", flat=True)[:limit]

        for podcast_id in podcast_ids:
            parse_podcast_feed.enqueue(podcast_id=podcast_id)
