from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model

from jcasts.podcasts import itunes
from jcasts.podcasts.emails import send_recommendations_email
from jcasts.podcasts.feed_parser import parse_feed
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.recommender import recommend

logger = get_task_logger(__name__)


@shared_task(name="jcasts.podcasts.crawl_itunes")
def crawl_itunes(limit: int = 300) -> None:
    itunes.crawl_itunes(limit)


@shared_task(name="jcasts.podcasts.send_recommendation_emails")
def send_recommendation_emails() -> None:
    for user in get_user_model().objects.filter(
        send_recommendations_email=True, is_active=True
    ):
        send_recommendations_email(user)


@shared_task(name="jcasts.podcasts.sync_podcast_feeds")
def sync_podcast_feeds(last_updated: int = 24) -> None:
    """Sync podcasts with RSS feeds. Fetch any without a pub date or
    pub_date > given period."""

    qs = (
        Podcast.objects.for_feed_sync(last_updated)
        .order_by("-pub_date")
        .values_list("rss", flat=True)
    )

    total = qs.count()

    logger.info(f"Syncing {total} podcasts")

    for counter, rss in enumerate(qs.iterator(), 1):
        sync_podcast_feed.delay(rss)


@shared_task(name="jcasts.podcasts.create_podcast_recommendations")
def create_podcast_recommendations() -> None:
    recommend()


@shared_task(name="jcasts.podcasts.sync_podcast_feed")
def sync_podcast_feed(rss: str, force_update: bool = False) -> None:
    try:
        podcast = Podcast.objects.get(rss=rss, active=True)
        if parse_feed(podcast, force_update=force_update):
            logger.info(f"Podcast {podcast} updated")

    except Podcast.DoesNotExist:
        logger.debug(f"No podcast found for RSS {rss}")
