import pytest
from django.core.management import call_command

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.tests.factories import (
    RecommendationFactory,
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
        recommendation = RecommendationFactory(recommended=subscription.podcast)
        EpisodeFactory(podcast=subscription.podcast)
        EpisodeFactory(podcast=recommendation.recommended)
        call_command("send_notifications")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
