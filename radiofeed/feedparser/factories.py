from __future__ import annotations

from datetime import datetime

from radiofeed.common.factories import (
    NotSet,
    datetime_notset,
    guid_notset,
    notset,
    text_notset,
    url_notset,
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
        "guid": guid_notset(guid),
        "title": text_notset(title),
        "media_url": url_notset(media_url),
        "pub_date": datetime_notset(pub_date),
        "media_type": notset(media_type, "audio/mpeg"),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": text_notset(title), **kwargs}
