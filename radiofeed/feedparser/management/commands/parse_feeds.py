import argparse
import contextlib
from concurrent.futures import wait
from typing import Final

from django.core.management.base import BaseCommand
from django.db.models import Count, F, QuerySet
from loguru import logger

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor

_VERBOSITY_NORMAL: Final = 1
_VERBOSITY_VERBOSE: Final = 2


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
        verbosity: int = options["verbosity"]

        if verbosity > _VERBOSITY_NORMAL:
            logger.enable("radiofeed.feedparser.feed_parser")
        if verbosity > _VERBOSITY_VERBOSE:
            logger.enable("radiofeed.http_client")

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
            scheduler.get_scheduled_podcasts()
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
