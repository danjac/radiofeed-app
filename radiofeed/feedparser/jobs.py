import logging

from django.db.models import Count, F, QuerySet
from scheduler import job

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

logger = logging.getLogger(__name__)


@job
def parse_feeds(*, limit: int = 360) -> None:
    """Parses RSS feeds of all scheduled podcasts."""
    client = get_client()

    execute_thread_pool(
        lambda podcast: _parse_feed(podcast, client),
        _get_scheduled_podcasts(limit),
    )


def _get_scheduled_podcasts(limit: int) -> QuerySet[Podcast]:
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


def _parse_feed(
    podcast: Podcast,
    client: Client,
) -> None:
    try:
        feed_parser.parse_feed(podcast, client)
        logger.debug("Parsed feed %s", podcast)
    except FeedParserError as e:
        logger.debug("Failed to parse feed %s: %s", podcast, e.parser_error)
