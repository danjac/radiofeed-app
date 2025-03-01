import argparse

from django.core.management.base import BaseCommand, CommandParser

from radiofeed.feedparser import opml_parser
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Django management command to parse an OPML file and import podcasts."""

    help = "Parse an OPML file and import podcasts."

    def add_arguments(self, parser: CommandParser) -> None:
        """Parse command line arguments."""

        parser.add_argument(
            "file",
            type=argparse.FileType("rb"),
            help="The OPML file to parse",
        )

        parser.add_argument(
            "--promote",
            action="store_true",
            help="Promote all imported podcasts",
        )

    def handle(self, **options) -> None:
        """Parses an OPML file and imports podcasts."""
        podcasts = Podcast.objects.bulk_create(
            [
                Podcast(
                    rss=rss,
                    promoted=options["promote"],
                )
                for rss in opml_parser.parse_opml(options["file"].read())
            ],
            ignore_conflicts=True,
        )

        if num_podcasts := len(podcasts):
            self.stdout.write(self.style.SUCCESS(f"{num_podcasts} podcasts imported"))
        else:
            self.stdout.write(self.style.ERROR("No podcasts found in OPML"))
