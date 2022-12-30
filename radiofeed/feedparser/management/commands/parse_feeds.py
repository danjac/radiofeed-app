from __future__ import annotations

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

import httpx

from django.core.management.base import BaseCommand

from radiofeed.common import user_agent
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

        except feed_parser.NotModified:
            self.stdout.write(self.style.NOTICE(f"{podcast} is not modified"))

        except feed_parser.Inaccessible:
            self.stdout.write(self.style.ERROR(f"{podcast} is no longer accessible"))

        except feed_parser.Duplicate:
            self.stdout.write(
                self.style.ERROR(f"{podcast} is a duplicate of another feed")
            )

        except feed_parser.Invalid:
            self.stdout.write(self.style.ERROR(f"{podcast} is temporarily unavailable"))

        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
