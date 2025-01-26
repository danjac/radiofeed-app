import pytest

from radiofeed.podcasts import emails
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestRecommendations:
    @pytest.fixture
    def address(self, user):
        return EmailAddressFactory(user=user)

    @pytest.mark.django_db
    def test_send_if_no_recommendations(self, address, mailoutbox):
        """If no recommendations, don't send."""
        PodcastFactory.create_batch(3)

        assert not emails.send_recommendations_email(address)
        assert len(mailoutbox) == 0

    @pytest.mark.django_db
    def test_send_promoted(self, address, mailoutbox):
        PodcastFactory.create_batch(3, promoted=True)

        emails.send_recommendations_email(address)
        assert len(mailoutbox) == 1

        assert mailoutbox[0].to == [address.email]
        assert address.user.recommended_podcasts.count() == 3

    @pytest.mark.django_db
    def test_has_recommendations(self, address, mailoutbox):
        first = SubscriptionFactory(subscriber=address.user).podcast
        second = SubscriptionFactory(subscriber=address.user).podcast
        third = SubscriptionFactory(subscriber=address.user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        # promoted
        PodcastFactory(promoted=True)

        emails.send_recommendations_email(address)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [address.email]
        assert address.user.recommended_podcasts.count() == 4

    @pytest.mark.django_db
    def test_already_recommended(self, address, mailoutbox):
        subscribed = SubscriptionFactory(subscriber=address.user).podcast
        recommended = RecommendationFactory(podcast=subscribed).recommended
        address.user.recommended_podcasts.add(recommended)

        assert not emails.send_recommendations_email(address)
        assert len(mailoutbox) == 0
