from __future__ import annotations

import functools

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    default_guid,
    default_now,
    default_text,
    default_url,
    set_default,
)
from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import default_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import default_user
from radiofeed.users.models import User


def create_episode(
    *,
    guid: str = NotSet,
    podcast: Podcast = NotSet,
    title: str = NotSet,
    description: str = NotSet,
    pub_date: datetime | None = NotSet,
    media_url: str = NotSet,
    media_type: str = NotSet,
    duration: str = NotSet,
    **kwargs,
) -> Episode:

    return Episode.objects.create(
        guid=default_guid(guid),
        podcast=default_podcast(podcast),
        title=default_text(title),
        description=default_text(description),
        pub_date=default_now(pub_date),
        media_url=default_url(media_url),
        media_type=set_default(media_type, "audio/mpeg"),
        duration=set_default(duration, "100"),
        **kwargs,
    )


default_episode = functools.partial(set_default, default_value=create_episode)


def create_bookmark(*, episode: Episode = NotSet, user: User = NotSet) -> Bookmark:
    return Bookmark.objects.create(
        episode=default_episode(episode), user=default_user(user)
    )


def create_audio_log(
    *,
    episode: Episode = NotSet,
    user: User = NotSet,
    listened: datetime = NotSet,
    current_time: int = NotSet,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=default_episode(episode),
        user=default_user(user),
        listened=default_now(listened),
        current_time=set_default(current_time, 1000),
    )
