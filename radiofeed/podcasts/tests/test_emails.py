# Third Party Libraries
import pytest

# Local
from ..emails import send_recommendation_email
from ..factories import RecommendationFactory, SubscriptionFactory

pytestmark = pytest.mark.django_db


class TestSendRecommendationEmail:
    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""

        send_recommendation_email(user)
        assert len(mailoutbox) == 0

    def test_send_if_sufficient_recommendations(self, user, mailoutbox):

        first = SubscriptionFactory(user=user).podcast
        second = SubscriptionFactory(user=user).podcast

        third = SubscriptionFactory(user=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        send_recommendation_email(user)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]

        assert user.recommended_podcasts.count() == 3
