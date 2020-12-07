# Standard Library
import uuid

# Django
from django.utils import timezone

# Third Party Libraries
from factory import DjangoModelFactory, Faker, LazyFunction, SubFactory

# RadioFeed
from radiofeed.podcasts.factories import PodcastFactory

# Local
from .models import Episode


class EpisodeFactory(DjangoModelFactory):

    guid = LazyFunction(lambda: uuid.uuid4().hex)
    podcast = SubFactory(PodcastFactory)
    title = Faker("text")
    description = Faker("text")
    media_url = Faker("url")
    media_type = "audio/mpeg"
    pub_date = LazyFunction(timezone.now)

    class Meta:
        model = Episode
