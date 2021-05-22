from django.core import mail
from django.test import TestCase

from audiotrails.podcasts.emails import send_recommendations_email
from audiotrails.podcasts.factories import FollowFactory, RecommendationFactory
from audiotrails.users.factories import UserFactory


class SendRecommendationEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def test_send_if_no_recommendations(self) -> None:
        """If no recommendations, don't send."""

        send_recommendations_email(self.user)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_if_sufficient_recommendations(self) -> None:

        first = FollowFactory(user=self.user).podcast
        second = FollowFactory(user=self.user).podcast
        third = FollowFactory(user=self.user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        send_recommendations_email(self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(self.user.recommended_podcasts.count(), 3)
