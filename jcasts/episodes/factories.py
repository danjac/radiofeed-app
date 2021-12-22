import uuid

from django.utils import timezone
from factory import Faker, LazyFunction, Sequence, SubFactory
from factory.django import DjangoModelFactory

from jcasts.episodes.models import AudioLog, Bookmark, Episode, QueueItem
from jcasts.podcasts.factories import PodcastFactory
from jcasts.users.factories import UserFactory


class EpisodeFactory(DjangoModelFactory):

    guid = LazyFunction(lambda: uuid.uuid4().hex)
    podcast = SubFactory(PodcastFactory)
    title = Faker("text")
    description = Faker("text")
    media_url = Faker("url")
    media_type = "audio/mpeg"
    pub_date = LazyFunction(timezone.now)
    duration = "100"

    class Meta:
        model = Episode


class BookmarkFactory(DjangoModelFactory):
    episode = SubFactory(EpisodeFactory)
    user = SubFactory(UserFactory)

    class Meta:
        model = Bookmark


class AudioLogFactory(DjangoModelFactory):
    episode = SubFactory(EpisodeFactory)
    user = SubFactory(UserFactory)
    updated = LazyFunction(timezone.now)
    current_time = 1000

    class Meta:
        model = AudioLog


class QueueItemFactory(DjangoModelFactory):
    episode = SubFactory(EpisodeFactory)
    user = SubFactory(UserFactory)
    position = Sequence(lambda n: n + 1)

    class Meta:
        model = QueueItem
