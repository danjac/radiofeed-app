import argparse
import sys

from django.core.management.base import BaseCommand

from radiofeed.podcasts import opml
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Django management command."""

    help = """Create new podcast feeds from OPML document."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "input",
            help="OPML file",
            type=argparse.FileType("r"),
            nargs="?",
            default=sys.stdin.buffer,
        )

    def handle(self, **options):
        """Handle implementation."""
        podcasts = Podcast.objects.bulk_create(
            [Podcast(rss=rss) for rss in opml.parse_opml(options["input"])],
            ignore_conflicts=True,
        )

        if num_podcasts := len(podcasts):
            self.stdout.write(self.style.SUCCESS(f"{num_podcasts} podcasts imported"))
        else:
            self.stdout.write("No podcasts found")
