import uuid
from datetime import datetime

from django.utils import timezone
from faker import Faker

from radiofeed.tests.factories import NotSet, resolve

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
        "guid": resolve(guid, lambda: uuid.uuid4().hex),
        "title": resolve(title, _faker.text),
        "pub_date": resolve(pub_date, timezone.now),
        "media_url": resolve(
            media_url,
            lambda: _faker.unique.url() + _faker.unique.file_name("audio"),
        ),
        "media_type": resolve(media_type, _faker.mime_type("audio")),
        **kwargs,
    }


def create_feed(title: str = NotSet, **kwargs) -> dict:
    return {"title": resolve(title, _faker.text), **kwargs}
