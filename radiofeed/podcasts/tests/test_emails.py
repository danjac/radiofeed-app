import pytest

from radiofeed.podcasts import emails
from radiofeed.podcasts.tests.factories import (
    create_podcast,
    create_recommendation,
    create_subscription,
)
from radiofeed.tests.factories import create_batch


class TestRecommendations:
    @pytest.mark.django_db()
    def test_send_if_no_recommendations(self, user, mailoutbox):
        """If no recommendations, don't send."""
        create_batch(create_podcast, 3)

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0

    @pytest.mark.django_db()
    def test_send_promoted(self, user, mailoutbox):
        create_batch(create_podcast, 3, promoted=True)
        emails.send_recommendations_email(user)
        assert len(mailoutbox) == 1

        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3

    @pytest.mark.django_db()
    def test_has_recommendations(self, user, mailoutbox):
        first = create_subscription(subscriber=user).podcast
        second = create_subscription(subscriber=user).podcast
        third = create_subscription(subscriber=user).podcast

        create_recommendation(podcast=first)
        create_recommendation(podcast=second)
        create_recommendation(podcast=third)

        # promoted
        create_podcast(promoted=True)

        emails.send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 4

    @pytest.mark.django_db()
    def test_already_recommended(self, user, mailoutbox):
        subscribed = create_subscription(subscriber=user).podcast
        recommended = create_recommendation(podcast=subscribed).recommended
        user.recommended_podcasts.add(recommended)

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0
