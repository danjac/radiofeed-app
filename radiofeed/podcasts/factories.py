from __future__ import annotations

import factory

from django.utils import timezone
from factory.django import DjangoModelFactory

from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import UserFactory


class CategoryFactory(DjangoModelFactory):
    name = factory.Sequence(lambda i: f"category-{i}")

    class Meta:
        model = Category


class PodcastFactory(DjangoModelFactory):
    rss = factory.Sequence(lambda i: f"https://example.com/{i}.xml")
    title = factory.Faker("text")
    pub_date = factory.LazyFunction(timezone.now)
    cover_url = "https://example.com/cover.jpg"
    owner = factory.Faker("name")
    link = factory.Faker("url")
    description = factory.Faker("text")

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
