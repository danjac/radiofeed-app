import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.utils import timezone

from . import itunes
from .emails import send_recommendations_email
from .models import Podcast
from .recommender import recommend
from .rss_parser import parse_rss
from .rss_parser.exceptions import RssParserError

logger = get_task_logger(__name__)


@shared_task(name="radiofeed.podcasts.crawl_itunes")
def crawl_itunes(limit: int = 300) -> None:
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
    # ignore any with persistent errors

    podcasts = Podcast.objects.filter(num_retries__lt=3).distinct()

    # get podcasts that haven't been synced yet
    for rss in (
        podcasts.filter(last_updated__isnull=True)
        .values_list("rss", flat=True)
        .iterator()
    ):
        sync_podcast_feed.delay(rss)

    # get podcasts not updated in last 12 hours
    for rss in (
        podcasts.filter(
            last_updated__isnull=False,
            last_updated__lt=timezone.now() - datetime.timedelta(hours=12),
        )
        .values_list("rss", flat=True)
        .iterator()
    ):
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
