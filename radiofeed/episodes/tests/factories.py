import uuid
from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import create_podcast
from radiofeed.tests.factories import NotSet, resolve
from radiofeed.users.models import User
from radiofeed.users.tests.factories import create_user

_faker = Faker()


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
        guid=resolve(guid, lambda: uuid.uuid4().hex),
        podcast=resolve(podcast, create_podcast),
        title=resolve(title, _faker.text),
        description=resolve(description, _faker.text),
        pub_date=resolve(pub_date, timezone.now),
        media_url=resolve(
            media_url,
            lambda: _faker.unique.url() + _faker.unique.file_name("audio"),
        ),
        media_type=resolve(media_type, _faker.mime_type("audio")),
        duration=resolve(duration, "100"),
        **kwargs,
    )


def create_bookmark(*, episode: Episode = NotSet, user: User = NotSet) -> Bookmark:
    return Bookmark.objects.create(
        episode=resolve(episode, create_episode),
        user=resolve(user, create_user),
    )


def create_audio_log(
    *,
    episode: Episode = NotSet,
    user: User = NotSet,
    listened: datetime = NotSet,
    current_time: int = NotSet,
) -> AudioLog:
    return AudioLog.objects.create(
        episode=resolve(episode, create_episode),
        user=resolve(user, create_user),
        listened=resolve(listened, timezone.now),
        current_time=resolve(current_time, 1000),
    )
