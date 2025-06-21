from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Count, F

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast

logger = get_task_logger(__name__)


@shared_task
def parse_feeds(limit: int = 360) -> None:
    """Parse feeds for all active podcasts."""

    podcast_ids = (
        Podcast.objects.scheduled()
        .alias(subscribers=Count("subscriptions"))
        .filter(active=True)
        .order_by(
            F("subscribers").desc(),
            F("promoted").asc(),
            F("parsed").asc(nulls_first=True),
        )
    ).values_list("pk", flat=True)[:limit]

    logger.info("Parsing feeds for %d podcasts", len(podcast_ids))

    for podcast_id in podcast_ids:
        parse_feed.delay(podcast_id)  # type: ignore[no-unreachable]


@shared_task
def parse_feed(podcast_id: int):
    """Parse a single podcast feed by its ID."""
    podcast = Podcast.objects.get(pk=podcast_id)
    try:
        feed_parser.parse_feed(podcast, get_client())
        logger.info("%s: Success", podcast)
    except FeedParserError as exc:
        logger.warning("%s: %s", podcast, exc.result.label)
