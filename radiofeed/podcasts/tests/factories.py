import factory
from django.utils import timezone

from radiofeed.podcasts.models import (
    Category,
    Podcast,
    Recommendation,
    Subscription,
)
from radiofeed.users.tests.factories import UserFactory


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
