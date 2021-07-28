from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_rq import get_scheduler, job

from jcasts.podcasts import itunes
from jcasts.podcasts.emails import send_recommendations_email
from jcasts.podcasts.feed_parser import parse_feed
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.recommender import recommend

# rename this to scheduler.py


# these can be just plain crons


def crawl_itunes(limit: int = 300) -> None:
    itunes.crawl_itunes(limit)


def send_recommendation_emails() -> None:
    for user in get_user_model().objects.filter(
        send_recommendations_email=True, is_active=True
    ):
        send_recommendations_email(user)


def create_podcast_recommendations() -> None:
    recommend()


def schedule_podcast_feeds() -> None:
    """Schedules recent podcasts to run at allotted time."""
    for podcast in (
        Podcast.objects.filter(
            active=True,
            frequency__isnull=False,
            pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD,
        ).order_by("-pub_date")
    ).iterator():
        schedule_podcast_feed(podcast)


@job
def sync_podcast_feed(rss: str, *, force_update: bool = False) -> None:

    # if not cache.set(f"sync_podcast_feed:{rss}", 1, 3600, nx=True):
    # logging.info(f"Task for podcast {rss} is locked")
    # return

    try:

        podcast = Podcast.objects.get(rss=rss, active=True)
    except Podcast.DoesNotExist:
        return

    success = parse_feed(podcast, force_update=force_update)
    logging.info(f"{podcast} pull {'OK' if success else 'FAIL'}")
    schedule_podcast_feed(podcast)


def schedule_podcast_feed(podcast: Podcast):
    if scheduled := podcast.get_next_scheduled():
        logging.info(f"{podcast} next scheduled pull: {scheduled}")
        get_scheduler("default").enqueue_at(scheduled, sync_podcast_feed, podcast.id)
