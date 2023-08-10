from argparse import ArgumentParser
from concurrent.futures import wait

import httpx
from django.core.management.base import BaseCommand
from django.db.models import Count, F, QuerySet

from radiofeed.client import http_client
from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


class Command(BaseCommand):
    """Parses RSS feeds."""

    help = """Parses RSS feeds of all scheduled podcasts."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--watch",
            help="Watch continuously",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--limit",
            help="Number of feeds to process",
            type=int,
            default=360,
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""

        while True:
            with http_client() as client, DatabaseSafeThreadPoolExecutor() as executor:
                wait(
                    executor.db_safe_map(
                        lambda podcast: self._parse_feed(client, podcast),
                        self._get_scheduled_podcasts(options["limit"]),
                    )
                )

            if not options["watch"]:
                break

    def _get_scheduled_podcasts(self, limit: int) -> QuerySet[Podcast]:
        return (
            scheduler.get_scheduled_podcasts()
            .alias(subscribers=Count("subscriptions"))
            .filter(active=True)
            .order_by(
                F("subscribers").desc(),
                F("promoted").desc(),
                F("parsed").asc(nulls_first=True),
            )[:limit]
        )

    def _parse_feed(self, client: httpx.Client, podcast: Podcast) -> None:
        try:
            feed_parser.FeedParser(podcast).parse(client)
            self.stdout.write(self.style.SUCCESS(f"parse feed ok: {podcast}"))
        except FeedParserError as exc:
            self.stderr.write(
                self.style.ERROR(f"parse feed {exc.parser_error}: {podcast}")
            )
