from __future__ import annotations

from radiofeed.factories import NotSet, Sequence, resolve
from radiofeed.podcasts.factories import create_podcast
from radiofeed.podcasts.models import Podcast
from radiofeed.websub.models import Subscription

_hubs = Sequence("https://example.com/hubs/hub-{n}")
_topics = Sequence("https://example.com/topics/feed-{n}")


def create_subscription(
    *, hub: str = NotSet, topic: str = NotSet, podcast: Podcast = NotSet, **kwargs
):
    return Subscription.objects.create(
        podcast=resolve(podcast, create_podcast),
        hub=resolve(hub, _hubs),
        topic=resolve(topic, _topics),
        **kwargs,
    )
