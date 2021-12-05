import factory

from factory.django import DjangoModelFactory

from jcasts.podcasts.factories import PodcastFactory
from jcasts.websub.models import Subscription


class SubscriptionFactory(DjangoModelFactory):
    hub = "https://pubsubhubbub.com"
    topic = factory.Sequence(lambda i: f"https://example.com/{i}.xml")
    podcast = factory.SubFactory(PodcastFactory)

    class Meta:
        model = Subscription
