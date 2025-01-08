import pytest

from radiofeed.podcasts import emails
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)


class TestRecommendations:
    @pytest.mark.django_db
    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""
        PodcastFactory.create_batch(3)

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0

    @pytest.mark.django_db
    def test_send_promoted(self, user, mailoutbox):
        PodcastFactory.create_batch(3, promoted=True)
        emails.send_recommendations_email(user)
        assert len(mailoutbox) == 1

        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3

    @pytest.mark.django_db
    def test_has_recommendations(self, user, mailoutbox):
        first = SubscriptionFactory(subscriber=user).podcast
        second = SubscriptionFactory(subscriber=user).podcast
        third = SubscriptionFactory(subscriber=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        # promoted
        PodcastFactory(promoted=True)

        emails.send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 4

    @pytest.mark.django_db
    def test_already_recommended(self, user, mailoutbox):
        subscribed = SubscriptionFactory(subscriber=user).podcast
        recommended = RecommendationFactory(podcast=subscribed).recommended
        user.recommended_podcasts.add(recommended)

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0
