from __future__ import annotations

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.common.factories import NotSet
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
    pub_date: datetime | NotSet | None = NotSet,
    cover_url: str | NotSet | None = NotSet,
    description: str = "",
    categories: list[Category] | None = None,
    **kwargs,
) -> Podcast:
    podcast = Podcast.objects.create(
        rss=rss or faker.unique.url(),
        title=title or faker.text(),
        cover_url="https://example.com/cover.jpg" if cover_url is NotSet else cover_url,
        description=description or faker.text(),
        pub_date=timezone.now() if pub_date is NotSet else pub_date,
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
        recommended=recommended or create_podcast(),
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
