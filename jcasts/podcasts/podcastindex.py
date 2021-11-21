from __future__ import annotations

import hashlib
import time

from datetime import datetime, timedelta

import requests

from django.conf import settings
from django.utils import timezone

from jcasts.podcasts.models import Podcast

BASE_URL = "https://api.podcastindex.org/api/1.0"


def fetch_new_feeds(frequency: timedelta, limit: int) -> int:
    now = timezone.now()
    data = get_response_data(
        "/recent/newfeeds",
        {
            "max": limit,
            "since": get_unix_timestamp(now - frequency),
        },
    )

    feeds = [item["url"] for item in data.get("feeds", [])]

    current_feeds = Podcast.objects.filter(
        rss__in=feeds,
    ).values_list("rss", flat=True)

    for_insert = [Podcast(rss=feed) for feed in feeds if feed not in current_feeds]
    Podcast.objects.bulk_create(for_insert, batch_size=500, ignore_conflicts=True)
    return len(for_insert)


def get_response_data(url: str, payload: dict | None) -> dict:

    unix_time = str(get_unix_timestamp(timezone.now()))

    auth = hashlib.sha1()  # nosec

    auth.update(
        "".join(
            (
                settings.PODCASTINDEX_API_KEY,
                settings.PODCASTINDEX_API_SECRET,
                unix_time,
            )
        ).encode("utf-8")
    )

    response = requests.get(
        BASE_URL + url,
        payload,
        headers={
            "Authorization": auth.hexdigest(),
            "Content-Type": "application/json",
            "User-Agent": "jcasts/0.1",
            "X-Auth-Key": settings.PODCASTINDEX_API_KEY,
            "X-Auth-Date": unix_time,
        },
    )

    response.raise_for_status()
    return response.json()


def get_unix_timestamp(dt: datetime) -> int:
    return round(time.mktime(dt.timetuple()))
