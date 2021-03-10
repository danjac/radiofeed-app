import factory

from django.utils import timezone
from factory.django import DjangoModelFactory

from radiofeed.users.factories import UserFactory

from .models import Category, Follow, Podcast, Recommendation


class CategoryFactory(DjangoModelFactory):
    name = factory.Sequence(lambda i: f"category-{i}")

    class Meta:
        model = Category


class PodcastFactory(DjangoModelFactory):
    rss = factory.Sequence(lambda i: f"https://example.com/{i}.xml")
    title = factory.Faker("text")
    description = factory.Faker("text")
    pub_date = factory.LazyFunction(timezone.now)
    cover_image = factory.django.ImageField()

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


class FollowFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Follow
