import factory
from django.utils import timezone

from radiofeed.podcasts.models import (
    Category,
    ItunesSearch,
    Podcast,
    Recommendation,
    Subscription,
)
from radiofeed.users.tests.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Category {n}")

    class Meta:
        model = Category


class ItunesSearchFactory(factory.django.DjangoModelFactory):
    search = factory.Faker("text")

    class Meta:
        model = ItunesSearch

    @classmethod
    def _create(cls, model_class, **kwargs):
        return model_class.objects.create(
            pk=model_class.objects.create_search_id(kwargs.get("search")),
            **kwargs,
        )


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
    frequency = 3
    similarity = 5

    podcast = factory.SubFactory(PodcastFactory)
    recommended = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Recommendation


class SubscriptionFactory(factory.django.DjangoModelFactory):
    subscriber = factory.SubFactory(UserFactory)
    podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Subscription
