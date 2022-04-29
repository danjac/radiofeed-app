from podtracker.podcasts.emails import send_recommendations_email
from podtracker.podcasts.factories import RecommendationFactory, SubscriptionFactory


class TestSendRecommendationEmail:
    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""

        send_recommendations_email(user)
        assert len(mailoutbox) == 0

    def test_send_if_sufficient_recommendations(self, user, mailoutbox):

        first = SubscriptionFactory(user=user).podcast
        second = SubscriptionFactory(user=user).podcast
        third = SubscriptionFactory(user=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3

    def test_send_if_sufficient_recommendations_and_episodes(self, user, mailoutbox):

        first = SubscriptionFactory(user=user).podcast
        second = SubscriptionFactory(user=user).podcast
        third = SubscriptionFactory(user=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3
