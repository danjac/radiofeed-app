import uuid

from datetime import datetime

from django.conf import settings
from django.utils import timezone
from factory import Faker, LazyFunction, Sequence, SubFactory
from factory.django import DjangoModelFactory

from audiotrails.podcasts.factories import PodcastFactory
from audiotrails.podcasts.models import Podcast
from audiotrails.users.factories import UserFactory

from .models import AudioLog, Episode, Favorite, QueueItem


class EpisodeFactory(DjangoModelFactory):

    guid: str = LazyFunction(lambda: uuid.uuid4().hex)
    podcast: Podcast = SubFactory(PodcastFactory)
    title: str = Faker("text")
    description: str = Faker("text")
    media_url: str = Faker("url")
    media_type: str = "audio/mpeg"
    pub_date: datetime = LazyFunction(timezone.now)

    class Meta:
        model = Episode


class FavoriteFactory(DjangoModelFactory):
    episode: Episode = SubFactory(EpisodeFactory)
    user: settings.AUTH_USER_MODEL = SubFactory(UserFactory)

    class Meta:
        model = Favorite


class AudioLogFactory(DjangoModelFactory):
    episode: Episode = SubFactory(EpisodeFactory)
    user: settings.AUTH_USER_MODEL = SubFactory(UserFactory)
    updated: datetime = LazyFunction(timezone.now)
    current_time: int = 1000

    class Meta:
        model = AudioLog


class QueueItemFactory(DjangoModelFactory):
    episode: Episode = SubFactory(EpisodeFactory)
    user: settings.AUTH_USER_MODEL = SubFactory(UserFactory)
    position: int = Sequence(lambda n: n + 1)

    class Meta:
        model = QueueItem
