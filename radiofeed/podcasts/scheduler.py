from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Podcast


def get_primary_podcasts() -> QuerySet:
    """Return any recent subscribed or promoted podcasts"""
    return (
        get_recent_podcasts()
        .with_subscribed()
        .filter(Q(promoted=True) | Q(subscribed=True))
    )


def get_frequent_podcasts() -> QuerySet:
    """Return any non-primary podcasts with pub date newer than 2 weeks"""
    return (
        get_recent_podcasts()
        .with_subscribed()
        .filter(
            promoted=False,
            subscribed=False,
        )
    )


def get_sporadic_podcasts() -> QuerySet:
    """Return any podcasts with pub date older than 2 weeks"""
    return get_scheduled_podcasts().filter(
        pub_date__lt=timezone.now() - timedelta(days=14),
    )


def get_recent_podcasts() -> QuerySet:
    return get_scheduled_podcasts().filter(
        Q(pub_date__isnull=True) | Q(pub_date__gt=timezone.now() - timedelta(days=14)),
    )


def get_scheduled_podcasts() -> QuerySet:
    return Podcast.objects.filter(
        Q(
            parsed__isnull=True,
        )
        | Q(parsed__lt=timezone.now() - timedelta(hours=3)),
        active=True,
    ).order_by(
        F("parsed").asc(nulls_first=True),
        F("pub_date").desc(nulls_first=True),
        F("created").desc(),
    )
