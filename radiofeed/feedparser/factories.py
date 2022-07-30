from __future__ import annotations

import uuid

import factory

from django.utils import timezone


class ItemFactory(factory.DictFactory):
    guid = factory.LazyFunction(lambda: uuid.uuid4().hex)
    title = factory.Faker("text")
    media_url = factory.Faker("url")
    media_type = "audio/mpeg"
    pub_date = factory.LazyFunction(timezone.now)


class FeedFactory(factory.DictFactory):
    title = factory.Faker("text")
