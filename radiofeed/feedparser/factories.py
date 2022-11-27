from __future__ import annotations

import uuid

from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.common.factories import NotSet

faker = Faker()


def create_item(
    guid: str = "",
    title: str = "",
    media_url: str = "",
    media_type: str = "audio/mpeg",
    pub_date: datetime | NotSet | None = NotSet,
    **kwargs,
) -> dict:
    return {
        "guid": guid or uuid.uuid4().hex,
        "title": title or faker.text(),
        "media_url": media_url or faker.unique.url(),
        "media_type": media_type,
        "pub_date": timezone.now() if pub_date is NotSet else pub_date,
        **kwargs,
    }


def create_feed(title: str = "", **kwargs) -> dict:
    return {"title": title or faker.text(), **kwargs}
