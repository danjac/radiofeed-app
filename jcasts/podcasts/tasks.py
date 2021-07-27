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


@shared_task(name="jcasts.podcasts.create_podcast_recommendations")
def create_podcast_recommendations() -> None:
    recommend()


@shared_task(name="jcasts.podcasts.sync_frequent_podcast_feeds")
def sync_frequent_podcast_feeds() -> None:
    for podcast_id in (
        Podcast.objects.frequent().order_by("-scheduled").values_list("id", flat=True)
    ):
        sync_podcast_feed.delay(podcast_id)


@shared_task(name="jcasts.podcasts.sync_podcast_feeds")
def sync_infrequent_podcast_feeds() -> None:
    for podcast_id in (
        Podcast.objects.infrequent().order_by("-pub_date").values_list("id", flat=True)
    ):
        sync_podcast_feed.delay(podcast_id)


@shared_task(name="jcasts.podcasts.sync_podcast_feed")
def sync_podcast_feed(podcast_id: int, *, force_update: bool = False) -> None:
    try:
        podcast = Podcast.objects.get(pk=podcast_id, active=True)
        logger.info(f"Sync podcast {podcast}")

        if parse_feed(podcast, force_update=force_update):
            logger.info(f"{podcast} updated")

    except Podcast.DoesNotExist:
        logger.debug(f"No podcast found for ID {podcast_id}")
