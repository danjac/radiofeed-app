import uuid

from django.utils import timezone
from factory.base import DictFactory
from factory.declarations import LazyFunction
from factory.faker import Faker


class ItemFactory(DictFactory):
    title = Faker("text")
    guid = LazyFunction(lambda: uuid.uuid4().hex)
    pub_date = LazyFunction(lambda: timezone.now().isoformat())
    categories = LazyFunction(list)

    media_url = "https://example.com/sample.mpg"
    media_type = "audio/mpeg"


class FeedFactory(DictFactory):
    title = Faker("text")
    pub_date = LazyFunction(lambda: timezone.now().isoformat())

    categories = LazyFunction(list)
    items = LazyFunction(list)
