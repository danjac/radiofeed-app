from __future__ import annotations

import uuid

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.common.factories import NotSet
from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import create_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import create_user
from radiofeed.users.models import User

faker = Faker()


def create_episode(
    *,
    guid: str = "",
    podcast: Podcast | None = None,
    title: str = "",
    description: str = "",
    pub_date: datetime | None = None,
    media_url: str | NotSet | None = NotSet,
    media_type: str = "audio/mpeg",
    duration: str = "100",
    **kwargs,
) -> Episode:

    return Episode.objects.create(
        guid=guid or uuid.uuid4().hex,
        podcast=podcast or create_podcast(),
        title=title or faker.text(),
        description=description or faker.text(),
        pub_date=pub_date or timezone.now(),
        media_url=faker.url() if media_url is NotSet else media_url,
        media_type=media_type,
        duration=duration,
        **kwargs,
    )


def create_bookmark(
    *, episode: Episode | None = None, user: User | None = None
) -> Bookmark:
    return Bookmark.objects.create(
        episode=episode or create_episode(),
        user=user or create_user(),
    )


def create_audio_log(
    *,
    episode: Episode | None = None,
    user: User | None = None,
    listened: datetime | None = None,
    current_time: int = 1000,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=episode or create_episode(),
        user=user or create_user(),
        listened=listened or timezone.now(),
        current_time=current_time,
    )
