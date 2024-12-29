from typing import Annotated

import typer
from django.db.models import Count, F, QuerySet
from django_typer.management import TyperCommand

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


class Command(TyperCommand):
    """Parse RSS feeds."""

    def handle(
        self,
        limit: Annotated[int, typer.Option(help="Number of feeds to process")] = 360,
    ) -> None:
        """Parses RSS feeds of all scheduled podcasts."""
        client = get_client()

        execute_thread_pool(
            lambda podcast: self._parse_feed(podcast, client),
            self._get_scheduled_podcasts(limit),
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
        try:
            feed_parser.parse_feed(podcast, client)
            self.stdout.write(self.style.SUCCESS(f"{podcast}: Success"))
        except FeedParserError as e:
            self.stdout.write(self.style.ERROR(f"{podcast}: {e.parser_error.label}"))
