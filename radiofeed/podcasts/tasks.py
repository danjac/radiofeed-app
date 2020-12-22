# Third Party Libraries
# Django
from django.contrib.auth import get_user_model

import requests
from celery import shared_task
from celery.utils.log import get_task_logger

# Local
from . import itunes
from .emails import send_recommendation_email
from .models import Podcast
from .recommender import PodcastRecommender
from .rss_parser import RssParser

logger = get_task_logger(__name__)


@shared_task(name="radiofeed.podcasts.crawl_itunes")
def crawl_itunes(limit=100):
    itunes.crawl_itunes(limit)


@shared_task(name="radiofeed.podcasts.send_recommendation_emails")
def send_recommendation_emails():
    users = get_user_model().objects.filter(
        send_recommendation_email=True, is_active=True
    )
    for user in users:
        send_recommendation_email(user)


@shared_task(name="radiofeed.podcasts.sync_podcast_feeds")
def sync_podcast_feeds():
    for podcast in Podcast.objects.all():
        sync_podcast_feed.delay(podcast.id)


@shared_task(name="radiofeed.podcasts.create_podcast_recommendations")
def create_podcast_recommendations():
    PodcastRecommender.recommend()


@shared_task(name="radiofeed.podcasts.sync_podcast_feed")
def sync_podcast_feed(podcast_id):
    try:
        podcast = Podcast.objects.get(pk=podcast_id)
        logger.info(f"Syncing podcast {podcast}")
        RssParser.parse_from_podcast(podcast)
    except Podcast.DoesNotExist:
        logger.error(f"No podcast found for id {podcast_id}")
    except requests.HTTPError as e:
        logger.exception(e)
