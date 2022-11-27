from __future__ import annotations

import functools

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    notset,
    notset_datetime,
    notset_guid,
    notset_text,
    notset_url,
)
from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import notset_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import notset_user
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
        guid=notset_guid(guid),
        podcast=notset_podcast(podcast),
        title=notset_text(title),
        description=notset_text(description),
        pub_date=notset_datetime(pub_date),
        media_url=notset_url(media_url),
        media_type=notset(media_type, "audio/mpeg"),
        duration=notset(duration, "100"),
        **kwargs,
    )


notset_episode = functools.partial(notset, default_value=create_episode)


def create_bookmark(*, episode: Episode = NotSet, user: User = NotSet) -> Bookmark:
    return Bookmark.objects.create(
        episode=notset_episode(episode), user=notset_user(user)
    )


def create_audio_log(
    *,
    episode: Episode = NotSet,
    user: User = NotSet,
    listened: datetime = NotSet,
    current_time: int = NotSet,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=notset_episode(episode),
        user=notset_user(user),
        listened=notset_datetime(listened),
        current_time=notset(current_time, 1000),
    )
