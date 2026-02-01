from django.utils import timezone
from factory import django
from factory.declarations import LazyFunction, Sequence, SubFactory
from factory.faker import Faker
from factory.helpers import post_generation

from radiofeed.podcasts.models import (
    Category,
    Podcast,
    Recommendation,
    Subscription,
)
from radiofeed.users.tests.factories import UserFactory


class CategoryFactory(django.DjangoModelFactory):
    name = Sequence(lambda n: f"Category {n}")

    class Meta:
        model = Category


class PodcastFactory(django.DjangoModelFactory):
    title = Faker("text")
    rss = Sequence(lambda n: f"https://{n}.example.com")
    pub_date = LazyFunction(timezone.now)
    cover_url = "https://example.com/cover.jpg"

    class Meta:
        model = Podcast

    @post_generation
    def categories(self, create, extracted, **kwargs):
        if create and extracted:
            self.categories.set(extracted)  # type: ignore[attr-defined]


class RecommendationFactory(django.DjangoModelFactory):
    score = 0.5

    podcast = SubFactory(PodcastFactory)
    recommended = SubFactory(PodcastFactory)

    class Meta:
        model = Recommendation


class SubscriptionFactory(django.DjangoModelFactory):
    subscriber = SubFactory(UserFactory)
    podcast = SubFactory(PodcastFactory)

    class Meta:
        model = Subscription
