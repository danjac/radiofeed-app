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
        sync_podcast_feed.delay(rss, counter, total)


@shared_task(name="jcasts.podcasts.create_podcast_recommendations")
def create_podcast_recommendations() -> None:
    recommend()


@shared_task(name="jcasts.podcasts.sync_podcast_feed")
def sync_podcast_feed(
    rss: str,
    counter: int | None = None,
    total: int | None = None,
    force_update: bool = False,
) -> None:
    try:
        podcast = Podcast.objects.get(rss=rss, active=True)
        new_episodes = parse_feed(podcast, force_update=force_update)
        logger.info(
            get_podcast_sync_message(
                podcast,
                new_episodes=len(new_episodes),
                counter=counter,
                total=total,
            )
        )

    except Podcast.DoesNotExist:
        logger.debug(f"No podcast found for RSS {rss}")


def get_podcast_sync_message(
    podcast: Podcast,
    new_episodes: int,
    counter: int | None = None,
    total: int | None = None,
) -> str:

    msg = f"Podcast {podcast} synced with feed: {new_episodes} new episodes"
    if total and counter:
        msg += f" ({counter}/{total})"
    return msg
