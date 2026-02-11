import logging

from django.contrib.sites.models import Site
from django.tasks import task  # type: ignore[reportMissingTypeStubs]

from radiofeed.client import get_client
from radiofeed.parsers.feed_parser import parse_feed
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.users.notifications import get_recipients, send_notification_email

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

        if genre_id:
            itunes.save_feeds_to_db(feeds)
            logger.info(
                "Saved %d iTunes feeds for country %s to database",
                len(feeds),
                country,
            )
        else:
            itunes.save_feeds_to_db(feeds, promoted=True)
            logger.info(
                "Saved %d iTunes popular feeds for country %s to database",
                len(feeds),
                country,
            )


@task
def send_podcast_recommendations(*, recipient_id: int, limit: int = 6) -> None:
    """Send podcast recommendations to users."""

    recipient = get_recipients().select_related("user").get(pk=recipient_id)
    site = Site.objects.get_current()
    if (
        podcasts := Podcast.objects.published()
        .recommended(recipient.user)
        .order_by("-relevance", "-pub_date")[:limit]
    ):
        send_notification_email(
            site,
            recipient,
            f"Hi, {recipient.user.name}, here are some podcasts you might like!",
            "podcasts/emails/recommendations.html",
            {
                "podcasts": podcasts,
            },
        )
        recipient.user.recommended_podcasts.add(*podcasts)
        logger.info("Sent podcast recommendations to user %s", recipient.user)
