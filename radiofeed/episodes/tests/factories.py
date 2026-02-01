import uuid

from django.utils import timezone
from factory import django
from factory.declarations import LazyFunction, SubFactory
from factory.faker import Faker

from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.tests.factories import PodcastFactory
from radiofeed.users.tests.factories import UserFactory


class EpisodeFactory(django.DjangoModelFactory):
    guid = LazyFunction(lambda: uuid.uuid4().hex)
    podcast = SubFactory(PodcastFactory)
    title = Faker("text")
    description = Faker("text")
    pub_date = LazyFunction(timezone.now)
    media_url = Faker("url")
    media_type = "audio/mpg"
    duration = "100"

    class Meta:
        model = Episode


class BookmarkFactory(django.DjangoModelFactory):
    user = SubFactory(UserFactory)
    episode = SubFactory(EpisodeFactory)

    class Meta:
        model = Bookmark


class AudioLogFactory(django.DjangoModelFactory):
    user = SubFactory(UserFactory)
    episode = SubFactory(EpisodeFactory)
    listened = LazyFunction(timezone.now)
    current_time = 1000

    class Meta:
        model = AudioLog
