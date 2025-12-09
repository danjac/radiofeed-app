from datetime import timedelta

import pytest
from django.utils import timezone

from listenwave.episodes.tasks import send_notifications
from listenwave.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from listenwave.podcasts.tests.factories import (
    SubscriptionFactory,
)
from listenwave.users.tests.factories import EmailAddressFactory


class TestSendNotifications:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(
            verified=True,
            primary=True,
        )

    @pytest.mark.django_db(transaction=True)
    def test_has_episodes(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
        )
        EpisodeFactory.create_batch(
            3,
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=1),
        )
        send_notifications.enqueue(recipient_id=recipient.id, days_since=6, limit=6)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]

    @pytest.mark.django_db(transaction=True)
    def test_is_bookmarked(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
        )
        episode = EpisodeFactory(
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=1),
        )
        BookmarkFactory(episode=episode, user=recipient.user)
        send_notifications.enqueue(recipient_id=recipient.id, days_since=6, limit=6)

        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_no_new_episodes(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        EpisodeFactory.create_batch(
            3,
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=10),
        )
        send_notifications.enqueue(recipient_id=recipient.id, days_since=6, limit=6)

        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_listened(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        episode = EpisodeFactory(
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=1),
        )
        AudioLogFactory(episode=episode, user=recipient.user)
        send_notifications.enqueue(recipient_id=recipient.id, days_since=6, limit=6)

        assert len(mailoutbox) == 0
