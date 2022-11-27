from __future__ import annotations

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    default_guid,
    default_now,
    default_text,
    default_url,
    set_default,
)


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
        "media_url": default_url(media_url),
        "pub_date": default_now(pub_date),
        "media_type": set_default(media_type, "audio/mpeg"),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": default_text(title), **kwargs}
