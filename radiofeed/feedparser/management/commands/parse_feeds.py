from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django_rq import enqueue

from radiofeed.feedparser import feed_parser, scheduler


class Command(BaseCommand):
    """Parses RSS feeds."""

    help = """Parses RSS feeds of all scheduled podcasts."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""
        for podcast_id in scheduler.get_podcasts_for_update().values_list(
            "pk", flat=True
        )[: options["limit"]]:
            enqueue(feed_parser.parse_feed, podcast_id)
