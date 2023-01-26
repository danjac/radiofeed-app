from __future__ import annotations

import uuid

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.factories import NotSet, counter, resolve

_faker = Faker()

_media_url_seq = counter("https://example.com/audio-{n}.mp3")


def create_item(
    guid: str = NotSet,
    title: str = NotSet,
    media_url: str = NotSet,
    media_type: str = NotSet,
    pub_date: datetime = NotSet,
    **kwargs,
) -> dict:
    return {
        "guid": resolve(guid, lambda: uuid.uuid4().hex),
        "title": resolve(title, _faker.text),
        "pub_date": resolve(pub_date, timezone.now),
        "media_url": resolve(media_url, lambda: next(_media_url_seq)),
        "media_type": resolve(media_type, "audio/mpeg"),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": resolve(title, _faker.text), **kwargs}
