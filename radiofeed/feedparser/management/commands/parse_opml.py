import argparse
import sys
from typing import IO

from django.core.management.base import BaseCommand

from radiofeed.feedparser.opml_parser import parse_opml
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """BaseCommand subclass"""

    help = "Create new podcast feeds from OPML document."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-line arguments"""
        parser.add_argument(
            "file",
            type=argparse.FileType("rb"),
            default=sys.stdin,
        )

        parser.add_argument(
            "--promote",
            action="store_true",
            default=False,
            help="Promote imported podcasts",
        )

    def handle(self, *args, **options) -> None:
        """Implementation of command."""
        promote: bool = options["promote"]
        reader: IO = options["file"]

        podcasts = Podcast.objects.bulk_create(
            [
                Podcast(
                    rss=rss,
                    promoted=promote,
                )
                for rss in parse_opml(reader.read())
            ],
            ignore_conflicts=True,
        )

        if num_podcasts := len(podcasts):
            self.stdout.write(self.style.SUCCESS(f"{num_podcasts} podcasts imported"))
        else:
            self.stdout.write(self.style.ERROR("No podcasts found"))
