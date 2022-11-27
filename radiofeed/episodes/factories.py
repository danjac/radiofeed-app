from __future__ import annotations

import uuid

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.common.factories import NotSet, notset
from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import create_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import create_user
from radiofeed.users.models import User

_faker = Faker()


def create_episode(
    *,
    guid: str = NotSet,
    podcast: Podcast = NotSet,
    title: str = NotSet,
    description: str = NotSet,
    pub_date: datetime | None = NotSet,
    media_url: str | None = NotSet,
    media_type: str = NotSet,
    duration: str = NotSet,
    **kwargs,
) -> Episode:

    return Episode.objects.create(
        guid=notset(guid, lambda: uuid.uuid4().hex),
        podcast=notset(podcast, create_podcast),
        title=notset(title, _faker.text),
        description=notset(description, _faker.text),
        pub_date=notset(pub_date, timezone.now),
        media_url=notset(media_url, _faker.url),
        media_type=notset(media_type, "audio/mpeg"),
        duration=notset(duration, "100"),
        **kwargs,
    )


def create_bookmark(*, episode: Episode = NotSet, user: User = NotSet) -> Bookmark:
    return Bookmark.objects.create(
        episode=notset(episode, create_episode), user=notset(user, create_user)
    )


def create_audio_log(
    *,
    episode: Episode = NotSet,
    user: User = NotSet,
    listened: datetime = NotSet,
    current_time: int = NotSet,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=notset(episode, create_episode),
        user=notset(user, create_user),
        listened=notset(listened, timezone.now),
        current_time=notset(current_time, 1000),
    )
