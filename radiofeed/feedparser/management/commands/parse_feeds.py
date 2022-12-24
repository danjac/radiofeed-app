from __future__ import annotations

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

import requests

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, rss_parser, scheduler
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
        with feed_parser.get_session() as session:
            with ThreadPoolExecutor() as executor:
                executor.map(
                    lambda podcast: self._parse_feed(podcast, session),
                    scheduler.scheduled_for_update()[: options["limit"]].iterator(),
                )

    def _parse_feed(self, podcast: Podcast, session: requests.Session) -> None:
        self.stdout.write(f"Parsing feed {podcast}...")

        try:
            feed_parser.parse_feed(podcast, session)

        except feed_parser.NotModified:
            self.stdout.write(self.style.NOTICE(f"{podcast} is not modified"))

        except feed_parser.Inaccessible:
            self.stdout.write(self.style.ERROR(f"{podcast} is no longer accessible"))

        except feed_parser.Duplicate:
            self.stdout.write(
                self.style.ERROR(f"{podcast} is a duplicate of another feed")
            )

        except rss_parser.RssParserError as e:
            self.stdout.write(self.style.ERROR(f"{podcast} RSS parser error {e}"))

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"{podcast} HTTP error {e}"))

        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
