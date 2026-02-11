import logging

from django.tasks import task  # type: ignore[reportMissingTypeStubs]

from radiofeed.client import get_client
from radiofeed.parsers.feed_parser import parse_feed
from radiofeed.podcasts.models import Podcast

logger = logging.getLogger(__name__)


@task
def parse_podcast_feed(*, podcast_id: int) -> Podcast.FeedStatus:
    """Parse the feed for a given podcast."""
    podcast = Podcast.objects.get(pk=podcast_id)
    logger.info("Parsing feed for podcast %s", podcast)
    with get_client() as client:
        result = parse_feed(podcast, client)
    logger.info("Parsed feed for podcast %s: %s", podcast, result.label)
    return result
