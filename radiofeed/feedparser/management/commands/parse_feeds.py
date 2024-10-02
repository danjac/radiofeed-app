import argparse
import contextlib
from concurrent.futures import wait

from django.core.management.base import BaseCommand
from django.db.models import Count, F, QuerySet

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


class Command(BaseCommand):
    """Command implementation."""

    help = "Parses RSS feeds of all scheduled podcasts."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add options."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=360,
            help="Number of feeds to process",
        )

    def handle(self, *args, **options) -> None:
        """Implementation of handle."""
        limit: int = options["limit"]

        client = get_client()

        with DatabaseSafeThreadPoolExecutor() as executor:
            wait(
                executor.db_safe_map(
                    lambda podcast: self._parse_feed(podcast, client),
                    self._get_scheduled_podcasts(limit),
                )
            )

    def _get_scheduled_podcasts(self, limit: int) -> QuerySet[Podcast]:
        return (
            Podcast.objects.scheduled()
            .alias(subscribers=Count("subscriptions"))
            .filter(active=True)
            .order_by(
                F("subscribers").desc(),
                F("promoted").desc(),
                F("parsed").asc(nulls_first=True),
            )[:limit]
        )

    def _parse_feed(self, podcast: Podcast, client: Client) -> None:
        with contextlib.suppress(FeedParserError):
            feed_parser.parse_feed(podcast, client)
