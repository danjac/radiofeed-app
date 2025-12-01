import uuid

import factory
from django.utils import timezone

from listenwave.episodes.models import AudioLog, Bookmark, Episode
from listenwave.podcasts.tests.factories import PodcastFactory
from listenwave.users.tests.factories import UserFactory


class EpisodeFactory(factory.django.DjangoModelFactory):
    guid = factory.LazyFunction(lambda: uuid.uuid4().hex)
    podcast = factory.SubFactory(PodcastFactory)
    title = factory.Faker("text")
    description = factory.Faker("text")
    pub_date = factory.LazyFunction(timezone.now)
    media_url = factory.Faker("url")
    media_type = "audio/mpg"
    duration = "100"

    class Meta:
        model = Episode


class BookmarkFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    episode = factory.SubFactory(EpisodeFactory)

    class Meta:
        model = Bookmark


class AudioLogFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    episode = factory.SubFactory(EpisodeFactory)
    listened = factory.LazyFunction(timezone.now)
    current_time = 1000

    class Meta:
        model = AudioLog
