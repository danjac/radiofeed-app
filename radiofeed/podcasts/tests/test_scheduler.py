from datetime import timedelta

from django.utils import timezone

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory


class TestScheduler:
    def test_get_primary_podcasts(self, db):

        now = timezone.now()

        subscribed = SubscriptionFactory().podcast
        promoted = PodcastFactory(promoted=True)

        # not subscribed or promoted, ignore
        PodcastFactory()

        # not scheduled, ignore
        SubscriptionFactory(podcast__parsed=now - timedelta(minutes=30))

        # not recent, ignore
        SubscriptionFactory(podcast__pub_date=now - timedelta(days=15))

        podcasts = scheduler.get_primary_podcasts()
        assert podcasts.count() == 2

        assert subscribed in podcasts
        assert promoted in podcasts

    def test_get_frequent_podcasts(self, db):

        now = timezone.now()

        # no pub date yet
        new = PodcastFactory(pub_date=None)
        recent = PodcastFactory(pub_date=now - timedelta(days=3))

        # subscribed, ignore
        SubscriptionFactory(podcast__pub_date=now - timedelta(days=3)).podcast

        # promoted, ignore
        PodcastFactory(promoted=True, pub_date=now - timedelta(days=3))

        # not recent, ignore
        PodcastFactory(pub_date=now - timedelta(days=15))

        # not scheduled
        PodcastFactory(
            pub_date=now - timedelta(days=3), parsed=now - timedelta(minutes=30)
        )

        podcasts = scheduler.get_frequent_podcasts()
        assert podcasts.count() == 2

        assert new in podcasts
        assert recent in podcasts

    def test_get_sporadic_podcasts(self, db):
        now = timezone.now()

        podcast = PodcastFactory(pub_date=now - timedelta(days=15))

        # no pub date, ignore
        PodcastFactory(pub_date=None)

        # recent, ignore
        PodcastFactory(pub_date=now - timedelta(days=3))

        # not scheduled
        PodcastFactory(
            pub_date=now - timedelta(days=15), parsed=now - timedelta(minutes=30)
        )

        podcasts = scheduler.get_sporadic_podcasts()
        assert podcasts.count() == 1
        assert podcasts.first() == podcast
