from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.feedparser import scheduler


class Command(BaseCommand):

    help = """
    Parses RSS feeds of all scheduled podcasts.
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, *args, **options) -> None:
        """Command handler implementation."""
        scheduler.schedule_for_update(options["limit"])
