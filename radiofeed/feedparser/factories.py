from __future__ import annotations

import itertools
import uuid

from datetime import datetime

from django.utils import timezone

from radiofeed.common.factories import NotSet, default, default_text

_media_url_seq = (f"https://example.com/audio-{n}.mp3" for n in itertools.count())


def create_item(
    guid: str = NotSet,
    title: str = NotSet,
    media_url: str = NotSet,
    media_type: str = NotSet,
    pub_date: datetime = NotSet,
    **kwargs,
) -> dict:
    return {
        "guid": default(guid, lambda: uuid.uuid4().hex),
        "title": default_text(title),
        "pub_date": default(pub_date, timezone.now),
        "media_url": default(media_url, next(_media_url_seq)),
        "media_type": default(media_type, "audio/mpeg"),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": default_text(title), **kwargs}
