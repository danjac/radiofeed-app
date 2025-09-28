import pytest
from django.core.management import call_command
from django.utils import timezone

from radiofeed.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.tests.factories import (
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestSendRecommendationsEmails:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(
            verified=True,
            primary=True,
        )

    @pytest.mark.django_db(transaction=True)
    def test_has_subscriptions(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        EpisodeFactory(podcast=subscription.podcast)
        call_command("send_notifications")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]

    @pytest.mark.django_db(transaction=True)
    def test_has_listened_to_podcast_recently(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        AudioLogFactory(
            episode__podcast=subscription.podcast,
            listened=timezone.now() - timezone.timedelta(days=1),
            user=recipient.user,
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_bookmarked(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        BookmarkFactory(
            episode__podcast=subscription.podcast,
            user=recipient.user,
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 0

    @pytest.mark.django_db(transaction=True)
    def test_has_not_listened_to_podcast_recently(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        AudioLogFactory(
            episode__podcast=subscription.podcast,
            listened=timezone.now() - timezone.timedelta(days=12),
            user=recipient.user,
        )
        call_command("send_notifications")
        assert len(mailoutbox) == 1

    @pytest.mark.django_db(transaction=True)
    def test_has_no_subscriptions(self, mailoutbox, recipient):
        call_command("send_notifications")
        assert len(mailoutbox) == 0
