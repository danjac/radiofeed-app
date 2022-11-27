from __future__ import annotations

import functools

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    default_name,
    default_now,
    default_text,
    default_url,
    set_default,
)
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import default_user
from radiofeed.users.models import User


def create_category(*, name: str = NotSet, **kwargs) -> Category:
    return Category.objects.create(name=default_name(name), **kwargs)


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
        rss=default_url(rss),
        title=default_text(title),
        description=default_text(description),
        pub_date=default_now(pub_date),
        cover_url=set_default(cover_url, "https://example.com/cover.jpg"),
        **kwargs,
    )

    if categories:
        podcast.categories.set(categories)

    return podcast


default_podcast = functools.partial(set_default, default_value=create_podcast)


def create_recommendation(
    *,
    podcast: Podcast = NotSet,
    recommended: Podcast = NotSet,
    frequency: int = NotSet,
    similarity: float = NotSet,
) -> Recommendation:
    return Recommendation.objects.create(
        podcast=default_podcast(podcast),
        recommended=default_podcast(recommended),
        frequency=set_default(frequency, 3),
        similarity=set_default(similarity, 0.5),
    )


def create_subscription(
    *,
    subscriber: User = NotSet,
    podcast: Podcast = NotSet,
) -> Subscription:

    return Subscription.objects.create(
        subscriber=default_user(subscriber),
        podcast=default_podcast(podcast),
    )
