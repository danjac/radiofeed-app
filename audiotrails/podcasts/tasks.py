from __future__ import annotations

import datetime

from urllib.error import URLError

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone

from audiotrails.podcasts import itunes
from audiotrails.podcasts.emails import send_recommendations_email
from audiotrails.podcasts.feed_parser import parse_feed
from audiotrails.podcasts.models import Podcast
from audiotrails.podcasts.recommender import recommend

logger = get_task_logger(__name__)


@shared_task(name="audiotrails.podcasts.crawl_itunes")
def crawl_itunes(limit: int = 300) -> None:
    itunes.crawl_itunes(limit)


@shared_task(name="audiotrails.podcasts.send_recommendation_emails")
def send_recommendation_emails() -> None:
    for user in get_user_model().objects.filter(
        send_recommendations_email=True, is_active=True
    ):
        send_recommendations_email(user)


@shared_task(name="audiotrails.podcasts.sync_podcast_feeds")
def sync_podcast_feeds() -> None:
    podcasts = Podcast.objects.all()

    querysets: tuple[QuerySet, QuerySet] = (
        # new podcasts
        podcasts.filter(last_updated__isnull=True),
        # podcasts updated > 12 hours ago
        podcasts.filter(
            last_updated__isnull=False,
            last_updated__lt=timezone.now() - datetime.timedelta(hours=12),
        ),
    )

    for qs in querysets:
        total = qs.count()
        logger.info(f"Syncing {total} podcasts")
        for counter, rss in enumerate(qs.values_list("rss", flat=True).iterator(), 1):
            sync_podcast_feed.delay(rss, counter, total)


@shared_task(name="audiotrails.podcasts.create_podcast_recommendations")
def create_podcast_recommendations() -> None:
    recommend()


@shared_task(name="audiotrails.podcasts.sync_podcast_feed")
def sync_podcast_feed(
    rss: str, counter: int | None = None, total: int | None = None
) -> None:
    try:
        podcast = Podcast.objects.get(rss=rss)
        msg = f"Syncing podcast {podcast}"
        if counter is not None and total is not None:
            msg += f":{counter}/{total}"
        logger.info(msg)
        if new_episodes := parse_feed(podcast):
            logger.info(f"Podcast {podcast} has {len(new_episodes)} new episode(s)")
    except Podcast.DoesNotExist:
        logger.debug(f"No podcast found for RSS {rss}")
    except URLError as e:
        logger.debug(f"Error syncing podcast RSS {rss} {e}")
