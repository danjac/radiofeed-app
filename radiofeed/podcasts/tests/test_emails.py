from __future__ import annotations

from django.contrib.sites.models import Site
from django.template import loader

from radiofeed.podcasts import emails
from radiofeed.podcasts.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)


class TestRecommendations:
    def test_template(self, user):
        podcasts = PodcastFactory.create_batch(3)
        content = loader.render_to_string(
            "podcasts/emails/recommendations.html",
            {"user": user, "podcasts": podcasts, "site": Site.objects.get_current()},
        )
        assert user.username in content

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

    def test_already_recommended(self, user, mailoutbox):

        subscribed = SubscriptionFactory(subscriber=user).podcast
        recommended = RecommendationFactory(podcast=subscribed).podcast
        user.recommended_podcasts.add(recommended)

        assert not emails.send_recommendations_email(user)
        assert len(mailoutbox) == 0
