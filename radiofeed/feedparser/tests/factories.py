import uuid

import factory
from django.utils import timezone


class ItemFactory(factory.DictFactory):
    title = factory.Faker("text")
    guid = factory.LazyFunction(lambda: uuid.uuid4().hex)
    pub_date = factory.LazyFunction(timezone.now)
    categories = factory.LazyFunction(list)

    media_url = "https://example.com/sample.mpg"
    media_type = "audio/mpeg"

    description = ""
    keywords = ""

    cover_url = None
    website = None

    explicit = "no"

    length = ""

    duration = "100"

    season = None
    episode = None

    episode_type = "full"


class FeedFactory(factory.DictFactory):
    title = factory.Faker("text")
    pub_date = factory.LazyFunction(timezone.now)

    categories = factory.LazyFunction(list)
    items = factory.LazyFunction(list)

    owner = ""
    description = ""

    language = "en"

    website = ""
    cover_url = ""

    funding_text = ""
    funding_url = None

    explicit = "no"
    complete = "no"
