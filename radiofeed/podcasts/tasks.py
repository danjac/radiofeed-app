import logging

from django.tasks import task  # type: ignore[reportMissingTypeStubs]

from radiofeed.client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.feed_parser import parse_feed
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


@task
def fetch_itunes_feeds(*, country: str, genre_id: int | None = None) -> None:
    """Fetch the top iTunes podcasts for a given country and genre."""
    with get_client() as client:
        try:
            feeds = itunes.fetch_top_feeds(client, country, genre_id)
        except itunes.ItunesError as e:
            logger.error("Error saving iTunes feeds to database: %s", e)
            return

        num_feeds = len(feeds)

        if genre_id:
            itunes.save_feeds_to_db(feeds)
            logger.info(
                "Saved %d iTunes feeds for country %s to database",
                num_feeds,
                country,
            )
        else:
            itunes.save_feeds_to_db(feeds, promoted=True)
            logger.info(
                "Saved %d iTunes popular feeds for country %s to database",
                num_feeds,
                country,
            )
