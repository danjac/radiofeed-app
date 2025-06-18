import argparse
import io

from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from radiofeed.feedparser.opml_parser import parse_opml
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Import podcasts from an OPML file."""

    help = "Import podcasts from an OPML file."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the import_opml command."""

        parser.add_argument(
            "file",
            type=argparse.FileType("rb"),
            help="Path to the OPML file to import.",
        )

    def handle(self, file: io.BufferedReader, **options) -> None:
        """Import podcasts from an OPML file."""
        Podcast.objects.bulk_create(
            (Podcast(rss=url) for url in parse_opml(file.read())),
            ignore_conflicts=True,
        )
        self.stdout.write(
            self.style.SUCCESS("Podcasts imported successfully from OPML file.")
        )
