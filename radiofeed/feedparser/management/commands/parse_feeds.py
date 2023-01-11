from __future__ import annotations

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

import httpx

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.podcasts.models import Podcast
from radiofeed.utils import user_agent


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

    def handle(self, **options) -> None:
        """Command handler implementation."""
        with httpx.Client(
            headers={"User-Agent": user_agent.user_agent()}, timeout=10
        ) as client, ThreadPoolExecutor() as executor:
            executor.map(
                lambda podcast: self._parse_feed(podcast, client),
                scheduler.scheduled_for_update()[: options["limit"]].iterator(),
            )

    def _parse_feed(self, podcast: Podcast, client: httpx.Client) -> None:
        self.stdout.write(f"Parsing feed {podcast}...")

        try:
            feed_parser.parse_feed(podcast, client)

        except FeedParserError:
            self.stdout.write(self.style.ERROR(f"{podcast} not updated"))

        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
