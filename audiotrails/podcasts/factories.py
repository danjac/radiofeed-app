from datetime import datetime

import factory

from django.conf import settings
from django.utils import timezone
from factory.django import DjangoModelFactory

from audiotrails.users.factories import UserFactory

from .models import Category, CoverImage, Follow, Podcast, Recommendation


class CategoryFactory(DjangoModelFactory):
    name: str = factory.Sequence(lambda i: f"category-{i}")

    class Meta:
        model = Category


class PodcastFactory(DjangoModelFactory):
    rss: str = factory.Sequence(lambda i: f"https://example.com/{i}.xml")
    title: str = factory.Faker("text")
    description: str = factory.Faker("text")
    pub_date: datetime = factory.LazyFunction(timezone.now)
    cover_image: CoverImage = factory.django.ImageField()

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
    podcast: Podcast = factory.SubFactory(PodcastFactory)
    recommended: Podcast = factory.SubFactory(PodcastFactory)

    frequency = 3
    similarity = 5.0

    class Meta:
        model = Recommendation


class FollowFactory(DjangoModelFactory):
    user: settings.AUTH_USER_MODEL = factory.SubFactory(UserFactory)
    podcast: Podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Follow
