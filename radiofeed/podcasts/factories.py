from __future__ import annotations

import itertools

from datetime import datetime

from django.utils import timezone

from radiofeed.common.factories import NotSet, default, default_text
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from radiofeed.users.factories import create_user
from radiofeed.users.models import User

_category_seq = (f"category-{n}" for n in itertools.count())
_rss_seq = (f"https://media.rss.com/podcast-{n}.xml" for n in itertools.count())


def create_category(*, name: str = NotSet, **kwargs) -> Category:
    return Category.objects.create(name=default(name, next(_category_seq)), **kwargs)


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
        rss=default(rss, next(_rss_seq)),
        title=default_text(title),
        description=default_text(description),
        pub_date=default(pub_date, timezone.now),
        cover_url=default(cover_url, "https://example.com/cover.jpg"),
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
        podcast=default(podcast, create_podcast),
        recommended=default(recommended, create_podcast),
        frequency=default(frequency, 3),
        similarity=default(similarity, 0.5),
    )


def create_subscription(
    *,
    subscriber: User = NotSet,
    podcast: Podcast = NotSet,
) -> Subscription:

    return Subscription.objects.create(
        subscriber=default(subscriber, create_user),
        podcast=default(podcast, create_podcast),
    )
