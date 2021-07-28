from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

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
    """Schedules recent podcasts to run at allotted time."""
    for podcast in (
        Podcast.objects.filter(
            active=True,
            frequency__isnull=False,
            pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD,
        ).order_by("-pub_date")
    ).iterator():
        if scheduled := podcast.get_next_scheduled():
            sync_podcast_feed.apply_async((podcast.id,), eta=scheduled)


@shared_task(name="jcasts.podcasts.sync_infrequent_podcast_feeds")
def sync_infrequent_podcast_feeds():
    """Matches any older feeds with pub date having same weekday. Should be run daily."""
    now = timezone.now()
    for podcast_id in (
        Podcast.objects.filter(
            active=True,
            pub_date__lt=now - settings.RELEVANCY_THRESHOLD,
            pub_date__iso_week_day=now.isoweekday(),
        )
        .order_by("-pub_date")
        .values_list("pk", flat=True)
        .iterator()
    ):
        sync_podcast_feed.delay(podcast_id)


@shared_task(name="jcasts.podcasts.sync_podcast_feed")
def sync_podcast_feed(podcast_id: int, *, force_update: bool = False) -> None:

    if not cache.set(f"sync_podcast_feed:{podcast_id}", 1, 3600, nx=True):
        logger.info(f"Task for podcast id {podcast_id} is locked")
        return

    try:

        podcast = Podcast.objects.get(pk=podcast_id, active=True)
    except Podcast.DoesNotExist:
        logger.debug(f"No podcast found for id {podcast_id}")
        return

    success = parse_feed(podcast, force_update=force_update)
    logger.info(f"{Podcast} pull {'OK' if success else 'FAIL'}")

    if scheduled := podcast.get_next_scheduled():
        logger.info(f"{podcast} next pull: {scheduled}")
        sync_podcast_feed.apply_async((podcast_id,), eta=scheduled)
