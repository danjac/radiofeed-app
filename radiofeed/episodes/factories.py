from __future__ import annotations

import functools

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    datetime_notset,
    guid_notset,
    notset,
    text_notset,
    url_notset,
)
from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import podcast_notset
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import user_notset
from radiofeed.users.models import User


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
        guid=guid_notset(guid),
        podcast=podcast_notset(podcast),
        title=text_notset(title),
        description=text_notset(description),
        pub_date=datetime_notset(pub_date),
        media_url=url_notset(media_url),
        media_type=notset(media_type, "audio/mpeg"),
        duration=notset(duration, "100"),
        **kwargs,
    )


episode_notset = functools.partial(notset, default_value=create_episode)


def create_bookmark(*, episode: Episode = NotSet, user: User = NotSet) -> Bookmark:
    return Bookmark.objects.create(
        episode=episode_notset(episode), user=user_notset(user)
    )


def create_audio_log(
    *,
    episode: Episode = NotSet,
    user: User = NotSet,
    listened: datetime = NotSet,
    current_time: int = NotSet,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=episode_notset(episode),
        user=user_notset(user),
        listened=datetime_notset(listened),
        current_time=notset(current_time, 1000),
    )
