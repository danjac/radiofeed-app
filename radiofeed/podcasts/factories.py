# Django
from django.utils import timezone

# Third Party Libraries
import factory
from factory.django import DjangoModelFactory

# RadioFeed
from radiofeed.users.factories import UserFactory

# Local
from .models import Category, Podcast, Subscription


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


class SubscriptionFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Subscription
