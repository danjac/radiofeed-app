import logging

from django.tasks import task  # type: ignore[reportMissingTypeStubs]

from listenwave.feedparser import feed_parser
from listenwave.http_client import get_client
from listenwave.podcasts.models import Podcast

logger = logging.getLogger(__name__)


@task
def parse_feed(*, podcast_id: int, **fields) -> Podcast.ParserResult:
    """Parse a podcast feed."""
    # TBD: add a flag for "queued"
    podcast = Podcast.objects.get(pk=podcast_id)
    logger.debug("Parsing feed for podcast %s", podcast)
    with get_client() as client:
        result = feed_parser.parse_feed(podcast, client, **fields)
    logger.debug("Parsed feed for podcast %s:%s", podcast, result)
    return result
