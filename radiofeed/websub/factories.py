from faker import Faker

from radiofeed.factories import NotSet, resolve
from radiofeed.podcasts.factories import create_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.websub.models import Subscription

_faker = Faker()


def create_subscription(
    *,
    hub: str = NotSet,
    topic: str = NotSet,
    podcast: Podcast = NotSet,
    **kwargs,
) -> Subscription:
    return Subscription.objects.create(
        podcast=resolve(podcast, create_podcast),
        hub=resolve(hub, _faker.url),
        topic=resolve(topic, _faker.url),
        **kwargs,
    )
