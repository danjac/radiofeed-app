from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.tests.factories import NotSet, resolve
from radiofeed.users.models import User
from radiofeed.users.tests.factories import create_user

_faker = Faker()


def create_category(*, name: str = NotSet, **kwargs) -> Category:
    return Category.objects.create(
        name=resolve(name, _faker.unique.domain_word), **kwargs
    )


def create_podcast(
    *,
    rss: str = NotSet,
    title: str = NotSet,
    pub_date: datetime | None = NotSet,
    cover_url: str | None = NotSet,
    description: str = NotSet,
    categories: list[Category] | None = None,
    **kwargs,
) -> Podcast:
    podcast = Podcast.objects.create(
        rss=resolve(rss, _faker.unique.url),
        title=resolve(title, _faker.text),
        description=resolve(description, _faker.text),
        pub_date=resolve(pub_date, timezone.now),
        cover_url=resolve(cover_url, "https://example.com/cover.jpg"),
        **kwargs,
    )

    if categories:
        podcast.categories.set(categories)

    return podcast


def create_recommendation(
    *,
    podcast: Podcast = NotSet,
    recommended: Podcast = NotSet,
    frequency: int = NotSet,
    similarity: float = NotSet,
) -> Recommendation:
    return Recommendation.objects.create(
        podcast=resolve(podcast, create_podcast),
        recommended=resolve(recommended, create_podcast),
        frequency=resolve(frequency, 3),
        similarity=resolve(similarity, 0.5),
    )


def create_subscription(
    *,
    subscriber: User = NotSet,
    podcast: Podcast = NotSet,
) -> Subscription:
    return Subscription.objects.create(
        subscriber=resolve(subscriber, create_user),
        podcast=resolve(podcast, create_podcast),
    )
