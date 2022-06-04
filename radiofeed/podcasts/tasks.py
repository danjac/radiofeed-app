from __future__ import annotations

from radiofeed.podcasts import emails, recommender  # , scheduler
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import feed_parser
from radiofeed.users.models import User


def recommend() -> None:
    """
    Generates podcast recommendations

    Runs 03:20 UTC every day
    """
    recommender.recommend()


def send_recommendations_emails() -> None:
    """
    Sends recommended podcasts to users

    Runs at 09:12 UTC every Monday
    """
    # send_recommendations_email.map(
    # User.objects.filter(
    # send_email_notifications=True,
    # is_active=True,
    # ).values_list("pk")
    # )


def schedule_podcast_feeds(limit: int = 300) -> None:
    """Schedules podcast feeds for update.

    Runs every 6 minutes
    """

    # parse_podcast_feed.map(
    # scheduler.schedule_podcasts_for_update().values_list("pk").distinct()[:limit]
    # )


def parse_podcast_feed(podcast_id: int) -> None:
    try:
        feed_parser.parse_podcast_feed(Podcast.objects.get(pk=podcast_id))
    except Podcast.DoesNotExist:
        pass


def send_recommendations_email(user_id: int) -> None:
    try:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
    except User.DoesNotExist:
        pass
