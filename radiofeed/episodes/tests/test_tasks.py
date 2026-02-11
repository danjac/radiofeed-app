from datetime import timedelta

import pytest
from django.utils import timezone

from radiofeed.episodes.tasks import send_episode_updates
from radiofeed.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.tests.factories import (
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestSendEpisodeUpdates:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(
            verified=True,
            primary=True,
        )

    @pytest.mark.django_db(transaction=True)
    def test_has_episodes(self, mailoutbox, recipient, _immediate_task_backend):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
        )
        EpisodeFactory.create_batch(
            3,
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=1),
        )
        send_episode_updates.enqueue(recipient_id=recipient.id)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]

    @pytest.mark.django_db(transaction=True)
    def test_is_bookmarked(self, mailoutbox, recipient, _immediate_task_backend):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
        )
        episode = EpisodeFactory(
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=1),
        )
        BookmarkFactory(episode=episode, user=recipient.user)
        send_episode_updates.enqueue(recipient_id=recipient.id)
        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_no_new_episodes(self, mailoutbox, recipient, _immediate_task_backend):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
        )
        EpisodeFactory.create_batch(
            3,
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=10),
        )
        send_episode_updates.enqueue(recipient_id=recipient.id)
        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_listened(self, mailoutbox, recipient, _immediate_task_backend):
        subscription = SubscriptionFactory(
            subscriber=recipient.user,
        )
        episode = EpisodeFactory(
            podcast=subscription.podcast,
            pub_date=timezone.now() - timedelta(days=1),
        )
        AudioLogFactory(
            episode=episode,
            user=recipient.user,
        )
        send_episode_updates.enqueue(recipient_id=recipient.id)
        assert len(mailoutbox) == 0
