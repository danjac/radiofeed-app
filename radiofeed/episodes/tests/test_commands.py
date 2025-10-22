import pytest
from django.core.management import call_command
from django.utils import timezone

from radiofeed.episodes.tests.factories import AudioLogFactory, EpisodeFactory
from radiofeed.podcasts.tests.factories import (
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


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
            podcast__pub_date=timezone.now() - timezone.timedelta(days=1),
        )
        EpisodeFactory.create_batch(
            3,
            podcast=subscription.podcast,
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]

    @pytest.mark.django_db(transaction=True)
    def test_no_new_episodes(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
            podcast__pub_date=timezone.now() - timezone.timedelta(days=10),
        )
        EpisodeFactory.create_batch(
            3,
            podcast=subscription.podcast,
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_recently_listened(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
            podcast__pub_date=timezone.now() - timezone.timedelta(days=1),
        )
        episode = EpisodeFactory(
            podcast=subscription.podcast,
        )
        AudioLogFactory(
            episode=episode,
            user=recipient.user,
            listened=timezone.now(),
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_not_recently_listened(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
            podcast__pub_date=timezone.now() - timezone.timedelta(days=1),
        )
        episode = EpisodeFactory(
            podcast=subscription.podcast,
        )
        AudioLogFactory(
            episode=episode,
            user=recipient.user,
            listened=timezone.now() - timezone.timedelta(days=10),
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
