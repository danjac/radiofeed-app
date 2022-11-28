from __future__ import annotations

import itertools
import uuid

from datetime import datetime

from django.utils import timezone

from radiofeed.common.factories import NotSet, default
from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import create_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import create_user
from radiofeed.users.models import User

_media_url_seq = (f"https://example.com/audio-{n}.mp3" for n in itertools.count())


def create_episode(
    *,
    guid: str = NotSet,
    podcast: Podcast = NotSet,
    title: str = NotSet,
    description: str = NotSet,
    pub_date: datetime = NotSet,
    media_url: str = NotSet,
    media_type: str = NotSet,
    duration: str = NotSet,
    **kwargs,
) -> Episode:

    return Episode.objects.create(
        guid=default(guid, lambda: uuid.uuid4().hex),
        podcast=default(podcast, create_podcast),
        title=default(title, "title"),
        description=default(description, "description"),
        pub_date=default(pub_date, timezone.now),
        media_url=default(media_url, next(_media_url_seq)),
        media_type=default(media_type, "audio/mpeg"),
        duration=default(duration, "100"),
        **kwargs,
    )


def create_bookmark(*, episode: Episode = NotSet, user: User = NotSet) -> Bookmark:
    return Bookmark.objects.create(
        episode=default(episode, create_episode),
        user=default(user, create_user),
    )


def create_audio_log(
    *,
    episode: Episode = NotSet,
    user: User = NotSet,
    listened: datetime = NotSet,
    current_time: int = NotSet,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=default(episode, create_episode),
        user=default(user, create_user),
        listened=default(listened, timezone.now),
        current_time=default(current_time, 1000),
    )
