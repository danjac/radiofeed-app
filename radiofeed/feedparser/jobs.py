import logging

from django.db.models import Count, F
from django.utils import timezone
from scheduler import job

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast

logger = logging.getLogger(__name__)


@job("default")
def parse_feeds(*, limit: int = 360) -> None:
    """Parses RSS feeds of all scheduled podcasts."""

    podcast_ids = list(
        Podcast.objects.scheduled()
        .alias(subscribers=Count("subscriptions"))
        .filter(
            active=True,
            queued__isnull=True,
        )
        .order_by(
            F("subscribers").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
        )
        .values_list("pk", flat=True)[:limit]
    )

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

    logger.debug("Parsing feeds for %d podcasts", len(podcast_ids))

    for podcast_id in podcast_ids:
        parse_feed.delay(podcast_id)  # type: ignore[union-attr]


@job("low")
def parse_feed(podcast_id: int) -> str:
    """Parses the RSS feed of a specific podcast."""

    podcast = Podcast.objects.get(id=podcast_id, active=True)
    logger.debug("Parsing feed for podcast %s", podcast)
    try:
        feed_parser.parse_feed(podcast, get_client())
        logger.debug("Parsed feed %s", podcast)
        return "success"
    except FeedParserError as e:
        logger.debug("Failed to parse feed %s: %s", podcast, e.parser_error)
        return str(e.parser_error)
