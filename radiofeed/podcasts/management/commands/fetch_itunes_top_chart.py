from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


class Command(BaseCommand):
    """Django command to crawl iTunes Top Chart."""

    help = "Crawl iTunes Top Chart"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command arguments."""

        parser.add_argument(
            "--location",
            type=str,
            help="iTunes location",
            default="gb",
        )

        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of podcasts to fetch",
            default=50,
        )

    def handle(self, **options):
        """Crawl iTunes Top Chart."""
        for podcast in itunes.fetch_top_chart(
            get_client(),
            location=options["location"],
            limit=options["limit"],
        ):
            self.stdout.write(self.style.SUCCESS(f"Podcast {podcast}"))
