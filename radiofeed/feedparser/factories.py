from __future__ import annotations

import uuid

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.common.factories import NotSet, notset

_faker = Faker()


def create_item(
    guid: str = NotSet,
    title: str = NotSet,
    media_url: str = NotSet,
    media_type: str = NotSet,
    pub_date: datetime = NotSet,
    **kwargs,
) -> dict:
    return {
        "guid": notset(guid, lambda: uuid.uuid4().hex),
        "title": notset(title, _faker.text()),
        "media_url": notset(media_url, _faker.unique.url),
        "media_type": notset(media_type, "audio/mpeg"),
        "pub_date": notset(pub_date, timezone.now),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": notset(title, _faker.text), **kwargs}
