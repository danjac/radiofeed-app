import requests

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model

from . import itunes
from .emails import send_recommendations_email
from .models import Podcast
from .recommender import PodcastRecommender
from .rss_parser import sync_rss_feed

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
    for rss in Podcast.objects.filter(num_retries__lt=3).values_list("rss", flat=True):
        sync_podcast_feed.delay(rss)


@shared_task(name="radiofeed.podcasts.create_podcast_recommendations")
def create_podcast_recommendations() -> None:
    PodcastRecommender.recommend()


@shared_task(name="radiofeed.podcasts.sync_podcast_feed")
def sync_podcast_feed(rss: str, force_update: bool = False) -> None:
    try:
        podcast = Podcast.objects.get(rss=rss)
        logger.info(f"Syncing podcast {podcast}")
        sync_rss_feed(podcast, force_update=force_update)
    except Podcast.DoesNotExist:
        logger.error(f"No podcast found for RSS {rss}")
    except requests.HTTPError as e:
        logger.error(f"Error fetching {rss}: {e}")
