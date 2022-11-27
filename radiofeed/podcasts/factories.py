from __future__ import annotations

import functools

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    datetime_notset,
    name_notset,
    notset,
    text_notset,
    url_notset,
)
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import user_notset
from radiofeed.users.models import User


def create_category(*, name: str = NotSet, **kwargs) -> Category:
    return Category.objects.create(name=name_notset(name), **kwargs)


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
        rss=url_notset(rss),
        title=text_notset(title),
        description=text_notset(description),
        pub_date=datetime_notset(pub_date),
        cover_url=notset(cover_url, "https://example.com/cover.jpg"),
        **kwargs,
    )

    if categories:
        podcast.categories.set(categories)

    return podcast


podcast_notset = functools.partial(notset, default_value=create_podcast)


def create_recommendation(
    *,
    podcast: Podcast = NotSet,
    recommended: Podcast = NotSet,
    frequency: int = NotSet,
    similarity: float = NotSet,
) -> Recommendation:
    return Recommendation.objects.create(
        podcast=podcast_notset(podcast),
        recommended=podcast_notset(recommended),
        frequency=notset(frequency, 3),
        similarity=notset(similarity, 0.5),
    )


def create_subscription(
    *,
    subscriber: User = NotSet,
    podcast: Podcast = NotSet,
) -> Subscription:

    return Subscription.objects.create(
        subscriber=user_notset(subscriber),
        podcast=podcast_notset(podcast),
    )
