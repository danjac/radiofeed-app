from __future__ import annotations

from huey.contrib.djhuey import db_task

from radiofeed.podcasts import emails
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import feed_parser
from radiofeed.users.models import User


@db_task()
def parse_podcast_feed(podcast_id: int) -> None:
    feed_parser.parse_podcast_feed(Podcast.objects.get(pk=podcast_id))


@db_task()
def send_recommendations_email(user_id: int) -> None:
    emails.send_recommendations_email(User.objects.get(pk=user_id))
