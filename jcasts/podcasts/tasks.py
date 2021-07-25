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


@shared_task(name="jcasts.podcasts.schedule_podcast_feeds")
def schedule_podcast_feeds() -> None:
    for podcast in Podcast.objects.filter(
        scheduled__isnull=True, pub_date__isnull=False, active=True
    ):
        _schedule_podcast_feed(podcast)


@shared_task(name="jcasts.podcasts.sync_podcast_feed")
def sync_podcast_feed(podcast_id: int, *, force_update: bool = False) -> None:
    try:
        podcast = Podcast.objects.get(pk=podcast_id, active=True)
        logger.info(f"Sync podcast {podcast}")

        parse_feed(podcast, force_update=force_update)

        # re-schedule for next time
        _schedule_podcast_feed(podcast)

    except Podcast.DoesNotExist:
        logger.debug(f"No podcast found for ID {podcast_id}")


def _schedule_podcast_feed(podcast: Podcast) -> None:
    if scheduled := podcast.get_next_scheduled_feed_update():
        logger.info(f"Podcast {podcast} scheduled to run at {scheduled.isoformat()}")
        # scheduling is tricky: setting ETA is ideal, but docker restarts
        # might nuke the scheduling
        sync_podcast_feed.apply_async((podcast.pk,), eta=scheduled)

    Podcast.objects.filter(pk=podcast.pk).update(scheduled=scheduled)
