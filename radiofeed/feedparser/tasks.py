import logging

from django.db.models import Count, F
from django_q.brokers import get_broker
from django_q.tasks import async_task

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast

logger = logging.getLogger(__name__)


def parse_feeds(limit: int = 360) -> None:
    """Parse feeds for all active podcasts."""

    podcasts = (
        Podcast.objects.scheduled()
        .alias(subscribers=Count("subscriptions"))
        .filter(active=True)
        .order_by(
            F("subscribers").desc(),
            F("itunes_ranking").asc(nulls_last=True),
            F("parsed").asc(nulls_first=True),
        )[:limit]
    )

    broker = get_broker()

    for podcast_id in podcasts.values_list("id", flat=True):
        async_task(parse_feed, podcast_id, broker=broker)


def parse_feed(podcast_id: int) -> None:
    """Parse a single podcast feed."""
    podcast = Podcast.objects.get(pk=podcast_id)
    try:
        feed_parser.parse_feed(podcast, get_client())
        logger.info("Podcast %s: OK", podcast)
    except FeedParserError as exc:
        logger.error("Podcast %s: %s", podcast, exc.parser_error.label)
