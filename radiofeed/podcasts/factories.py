from __future__ import annotations

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import create_user
from radiofeed.users.models import User

faker = Faker()


def create_category(*, name: str = "", **kwargs) -> Category:
    return Category.objects.create(name=name or faker.name(), **kwargs)


def create_podcast(
    *,
    rss: str = "",
    title: str = "",
    pub_date: datetime | None = None,
    cover_url="https://example.com/cover.jpg",
    description: str = "",
    categories: list[Category] or None = None,
    **kwargs,
) -> Podcast:
    podcast = Podcast.objects.create(
        rss=rss or faker.url(),
        title=title or faker.text(),
        cover_url=cover_url,
        description=description or faker.text(),
        pub_date=pub_date or timezone.now(),
        **kwargs,
    )

    if categories:
        podcast.categories.set(categories)

    return podcast


def create_recommendation(
    *,
    podcast: Podcast | None = None,
    recommended: Podcast | None = None,
    frequency: int = 3,
    similarity: float = 5.0,
) -> Recommendation:
    return Recommendation.objects.create(
        podcast=podcast or create_podcast(),
        recommened=recommended or create_podcast(),
        frequency=frequency,
        similarity=similarity,
    )


def create_subscription(
    *, subscriber: User | None = None, podcast: Podcast | None = None
) -> Subscription:

    return Subscription.objects.create(
        subscriber=subscriber or create_user(),
        podcast=podcast or create_podcast(),
    )
