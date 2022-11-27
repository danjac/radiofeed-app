from __future__ import annotations

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    notset,
    notset_datetime,
    notset_name,
    notset_text,
    notset_unique_url,
)
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import create_user
from radiofeed.users.models import User


def create_category(*, name: str = NotSet, **kwargs) -> Category:
    return Category.objects.create(name=notset_name(name), **kwargs)


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
        rss=notset_unique_url(rss),
        title=notset_text(title),
        description=notset_text(description),
        pub_date=notset_datetime(pub_date),
        cover_url=notset(cover_url, "https://example.com/cover.jpg"),
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
        podcast=notset(podcast, create_podcast),
        recommended=notset(recommended, create_podcast),
        frequency=notset(frequency, 3),
        similarity=notset(similarity, 0.5),
    )


def create_subscription(
    *,
    subscriber: User = NotSet,
    podcast: Podcast = NotSet,
) -> Subscription:

    return Subscription.objects.create(
        subscriber=notset(subscriber, create_user),
        podcast=notset(podcast, create_podcast),
    )
