from __future__ import annotations

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    notset,
    notset_datetime,
    notset_guid,
    notset_text,
    notset_unique_url,
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
        "guid": notset_guid(guid),
        "title": notset_text(title),
        "media_url": notset_unique_url(media_url),
        "pub_date": notset_datetime(pub_date),
        "media_type": notset(media_type, "audio/mpeg"),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": notset_text(title), **kwargs}
