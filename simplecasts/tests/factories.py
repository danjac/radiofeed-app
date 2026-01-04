import uuid

import factory
from allauth.account.models import EmailAddress
from django.utils import timezone

from simplecasts.models import (
    AudioLog,
    Bookmark,
    Category,
    Episode,
    Podcast,
    Recommendation,
    Subscription,
    User,
)


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.django.Password("testpass")

    class Meta:
        model = User


class EmailAddressFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda a: a.user.email)
    verified = True

    class Meta:
        model = EmailAddress


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Category {n}")

    class Meta:
        model = Category


class PodcastFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text")
    rss = factory.Sequence(lambda n: f"https://{n}.example.com")
    pub_date = factory.LazyFunction(timezone.now)
    cover_url = "https://example.com/cover.jpg"

    class Meta:
        model = Podcast

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        if create and extracted:
            self.categories.set(extracted)


class RecommendationFactory(factory.django.DjangoModelFactory):
    score = 0.5

    podcast = factory.SubFactory(PodcastFactory)
    recommended = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Recommendation


class SubscriptionFactory(factory.django.DjangoModelFactory):
    subscriber = factory.SubFactory(UserFactory)
    podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Subscription


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
