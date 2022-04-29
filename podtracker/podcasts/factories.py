import uuid

import factory

from django.utils import timezone
from factory import DictFactory, Faker, LazyFunction
from factory.django import DjangoModelFactory

from podtracker.podcasts.models import Category, Podcast, Recommendation, Subscription
from podtracker.users.factories import UserFactory


class FeedFactory(DictFactory):
    title = Faker("text")
    description = Faker("text")
    link = Faker("url")
    cover_url = Faker("url")
    explicit = False


class ItemFactory(DictFactory):

    guid = LazyFunction(lambda: uuid.uuid4().hex)
    pub_date = LazyFunction(lambda: timezone.now().isoformat())
    title = Faker("text")
    description = Faker("text")
    media_url = Faker("url")
    media_type = "audio/mpeg"
    length = 10000000
    duration = "100"
    explicit = False
    cover_url = None


class CategoryFactory(DjangoModelFactory):
    name = factory.Sequence(lambda i: f"category-{i}")

    class Meta:
        model = Category


class PodcastFactory(DjangoModelFactory):
    rss = factory.Sequence(lambda i: f"https://example.com/{i}.xml")
    title = factory.Faker("text")
    description = factory.Faker("text")
    pub_date = factory.LazyFunction(timezone.now)
    cover_url = "https://example.com/cover.jpg"

    class Meta:
        model = Podcast

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for category in extracted:
                self.categories.add(category)


class RecommendationFactory(DjangoModelFactory):
    podcast = factory.SubFactory(PodcastFactory)
    recommended = factory.SubFactory(PodcastFactory)

    frequency = 3
    similarity = 5.0

    class Meta:
        model = Recommendation


class SubscriptionFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Subscription
