import pytest

from radiofeed.podcasts import emails
from radiofeed.podcasts.factories import create_recommendation, create_subscription


class TestRecommendations:
    @pytest.mark.django_db
    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0

    @pytest.mark.django_db
    def test_sufficient_recommendations(self, user, mailoutbox):
        first = create_subscription(subscriber=user).podcast
        second = create_subscription(subscriber=user).podcast
        third = create_subscription(subscriber=user).podcast

        create_recommendation(podcast=first)
        create_recommendation(podcast=second)
        create_recommendation(podcast=third)

        assert emails.send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3

    @pytest.mark.django_db
    def test_already_recommended(self, user, mailoutbox):
        subscribed = create_subscription(subscriber=user).podcast
        recommended = create_recommendation(podcast=subscribed).podcast
        user.recommended_podcasts.add(recommended)

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0
