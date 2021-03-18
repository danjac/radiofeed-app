import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from . import itunes
from .emails import send_recommendations_email
from .models import Podcast
from .recommender import recommend
from .rss_parser import RssParserError, parse_rss

logger = get_task_logger(__name__)


@shared_task(name="radiofeed.podcasts.crawl_itunes")
def crawl_itunes(limit: int = 100) -> None:
    itunes.crawl_itunes(limit)


@shared_task(name="radiofeed.podcasts.send_recommendation_emails")
def send_recommendation_emails() -> None:
    users = get_user_model().objects.filter(
        send_recommendations_email=True, is_active=True
    )
    for user in users:
        send_recommendations_email(user)


@shared_task(name="radiofeed.podcasts.sync_podcast_feeds")
def sync_podcast_feeds() -> None:
    # get podcasts that haven't been updated in last 12 hours
    podcasts = Podcast.objects.filter(
        Q(last_updated__lt=timezone.now() - datetime.timedelta(hours=12))
        | Q(last_updated__isnull=True),
        num_retries__lt=3,
    ).distinct()
    for rss in podcasts.values_list("rss", flat=True):
        sync_podcast_feed.delay(rss)


@shared_task(name="radiofeed.podcasts.create_podcast_recommendations")
def create_podcast_recommendations() -> None:
    recommend()


@shared_task(name="radiofeed.podcasts.sync_podcast_feed")
def sync_podcast_feed(rss: str, *, force_update: bool = False) -> None:
    try:
        podcast = Podcast.objects.get(rss=rss)
        logger.info(f"Syncing podcast {podcast}")
        if episodes := parse_rss(podcast, force_update=force_update):
            logger.info(f"Podcast {podcast} has {len(episodes)} new episode(s)")
    except Podcast.DoesNotExist:
        logger.error(f"No podcast found for RSS {rss}")
    except RssParserError as e:
        logger.error(f"Error fetching {rss}: {e}")
