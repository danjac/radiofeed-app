from django.core.management import BaseCommand, CommandParser
from django.db.models import Case, Count, IntegerField, QuerySet, When

from radiofeed.podcasts import tasks
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Django management command to parse feeds for all active podcasts."""

    help = "Parse feeds for all active podcasts."

    def add_arguments(self, parser: CommandParser) -> None:
        """Parse command-line arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=360,
            help="The maximum number of podcasts to parse.",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Parse feeds for all active podcasts."""
        self.stdout.write(f"Parsing feeds for up to {limit} podcasts...")
        for podcast_id in self._get_scheduled_podcasts().values_list(
            "pk",
            flat=True,
        )[:limit]:
            tasks.parse_podcast_feed.enqueue(podcast_id=podcast_id)

    def _get_scheduled_podcasts(self) -> QuerySet[Podcast]:
        return (
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
        )
