from datetime import timedelta

from jcasts.episodes.emails import send_new_episodes_email
from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts.factories import SubscriptionFactory


class TestSendNewEpisodesEmail:
    def test_send_if_no_episodes(self, user, mailoutbox):
        """If no recommendations, don't send."""

        send_new_episodes_email(user, timedelta(days=7))
        assert len(mailoutbox) == 0

    def test_send_if_insufficient_episodes(self, user, mailoutbox):
        podcast = SubscriptionFactory(user=user).podcast
        EpisodeFactory(podcast=podcast)

        send_new_episodes_email(user, timedelta(days=7))

        assert len(mailoutbox) == 0

    def test_send_if_sufficient_episodes(self, user, mailoutbox):
        for _ in range(3):
            podcast = SubscriptionFactory(user=user).podcast
            EpisodeFactory(podcast=podcast)

        send_new_episodes_email(user, timedelta(days=7))

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
