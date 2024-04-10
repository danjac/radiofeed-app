import uuid

import factory
from django.utils import timezone


class ItemFactory(factory.DictFactory):
    title = factory.Faker("text")
    guid = factory.LazyFunction(lambda: uuid.uuid4().hex)
    pub_date = factory.LazyFunction(lambda: timezone.now().isoformat())
    categories = factory.LazyFunction(list)

    media_url = "https://example.com/sample.mpg"
    media_type = "audio/mpeg"


class FeedFactory(factory.DictFactory):
    title = factory.Faker("text")
    pub_date = factory.LazyFunction(lambda: timezone.now().isoformat())

    categories = factory.LazyFunction(list)
    items = factory.LazyFunction(list)
