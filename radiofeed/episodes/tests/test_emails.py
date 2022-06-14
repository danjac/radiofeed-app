from datetime import timedelta

from django.utils import timezone

from radiofeed.episodes.emails import send_new_episodes_email
from radiofeed.episodes.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.factories import SubscriptionFactory


class TestSendNewEpisodesEmail:
    def test_no_subscriptions(self, user, mailoutbox):

        assert not send_new_episodes_email(user, timedelta(days=7))
        assert len(mailoutbox) == 0

    def test_already_listened_or_bookmarked(self, user, mailoutbox):

        BookmarkFactory(
            user=user, episode__podcast=SubscriptionFactory(user=user).podcast
        )
        AudioLogFactory(
            user=user, episode__podcast=SubscriptionFactory(user=user).podcast
        )
        AudioLogFactory(
            user=user, episode__podcast=SubscriptionFactory(user=user).podcast
        )

        assert not send_new_episodes_email(user, timedelta(days=7))
        assert len(mailoutbox) == 0

    def test_send_insufficient_episodes(self, user, mailoutbox):
        podcast = SubscriptionFactory(user=user).podcast
        EpisodeFactory(podcast=podcast)

        assert not send_new_episodes_email(user, timedelta(days=7))
        assert len(mailoutbox) == 0

    def test_no_episodes_within_time_range(self, user, mailoutbox):
        pub_date = timezone.now() - timedelta(days=14)

        for _ in range(3):
            EpisodeFactory(
                podcast=SubscriptionFactory(
                    user=user, podcast__pub_date=pub_date
                ).podcast
            )

        assert not send_new_episodes_email(user, timedelta(days=7))
        assert len(mailoutbox) == 0

    def test_sufficient_episodes(self, user, mailoutbox):
        for _ in range(3):
            EpisodeFactory(podcast=SubscriptionFactory(user=user).podcast)

        assert send_new_episodes_email(user, timedelta(days=7))
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
