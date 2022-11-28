from __future__ import annotations

import itertools

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    default_guid,
    default_now,
    default_text,
    set_default,
)

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
        "guid": default_guid(guid),
        "title": default_text(title),
        "pub_date": default_now(pub_date),
        "media_url": set_default(media_url, next(_media_url_seq)),
        "media_type": set_default(media_type, "audio/mpeg"),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": default_text(title), **kwargs}
