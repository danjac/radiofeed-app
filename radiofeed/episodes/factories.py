from __future__ import annotations

import uuid

from django.utils import timezone
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory

from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.users.factories import UserFactory


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
    listened = LazyFunction(timezone.now)
    current_time = 1000

    class Meta:
        model = AudioLog
