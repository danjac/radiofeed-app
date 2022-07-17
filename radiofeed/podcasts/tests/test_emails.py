from __future__ import annotations

from radiofeed.podcasts import emails
from radiofeed.podcasts.factories import RecommendationFactory, SubscriptionFactory


class TestRecommendations:
    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0

    def test_sufficient_recommendations(self, user, mailoutbox):

        first = SubscriptionFactory(subscriber=user).podcast
        second = SubscriptionFactory(subscriber=user).podcast
        third = SubscriptionFactory(subscriber=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        assert emails.send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3
