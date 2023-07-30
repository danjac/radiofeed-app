from argparse import ArgumentParser
from collections.abc import Iterator
from concurrent.futures import wait

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, F

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.futures import DatabaseSafeThreadPoolExecutor
from radiofeed.podcasts.models import Podcast


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
            with self._get_client() as client, DatabaseSafeThreadPoolExecutor() as executor:
                futures = executor.db_safe_map(
                    lambda podcast_id: self._parse_feed(client, podcast_id),
                    self._get_scheduled_podcast_ids(
                        options["limit"],
                    ),
                )

            wait(futures)

            if not options["watch"]:
                break

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": settings.USER_AGENT,
            }
        )

    def _get_scheduled_podcast_ids(self, limit: int) -> Iterator[int]:
        return (
            scheduler.get_scheduled_podcasts()
            .alias(subscribers=Count("subscriptions"))
            .filter(active=True)
            .order_by(
                F("subscribers").desc(),
                F("promoted").desc(),
                F("parsed").asc(nulls_first=True),
            )
            .values_list("pk", flat=True)
            .distinct()[:limit]
        )

    def _parse_feed(self, client: httpx.Client, podcast_id: int) -> None:
        podcast = Podcast.objects.get(pk=podcast_id)
        try:
            feed_parser.FeedParser(podcast).parse(client)
            self.stdout.write(self.style.SUCCESS(f"parse feed ok: {podcast}"))
        except FeedParserError as e:
            self.stderr.write(
                self.style.ERROR(f"parse feed {e.parser_error}: {podcast}")
            )
