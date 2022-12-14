from __future__ import annotations

import itertools

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

import httpx

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Parses RSS feeds."""

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
        with feed_parser.get_client() as client:

            with ThreadPoolExecutor() as executor:
                executor.map(
                    lambda podcast: self._parse_feed(podcast, client),
                    itertools.islice(
                        scheduler.scheduled_for_update(),
                        options["limit"],
                    ),
                )

    def _parse_feed(self, podcast: Podcast, client: httpx.Client) -> None:
        self.stdout.write(f"Parsing feed {podcast}...")
        result = feed_parser.parse_feed(podcast, client)
        style = self.style.SUCCESS if result else self.style.NOTICE
        self.stdout.write(style(f"Parsing done for {podcast}: {result}"))
