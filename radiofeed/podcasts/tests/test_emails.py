from radiofeed.podcasts.emails import send_recommendations_email
from radiofeed.podcasts.factories import RecommendationFactory, SubscriptionFactory


class TestSendRecommendationEmail:
    def test_user_not_found(self, db, mailoutbox):
        assert not send_recommendations_email(1234)
        assert len(mailoutbox) == 0

    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""

        assert not send_recommendations_email(user.id)
        assert len(mailoutbox) == 0

    def test_sufficient_recommendations(self, user, mailoutbox):

        first = SubscriptionFactory(user=user).podcast
        second = SubscriptionFactory(user=user).podcast
        third = SubscriptionFactory(user=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        assert send_recommendations_email(user.id)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3
