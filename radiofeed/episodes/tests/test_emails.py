from datetime import timedelta

import pytest
from django.utils import timezone

from radiofeed.episodes.emails import send_new_episodes_email
from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.tests.factories import SubscriptionFactory


class TestNewEpisodesEmail:
    @pytest.mark.django_db()
    def test_email_sent(self, user, episode, mailoutbox):
        SubscriptionFactory(podcast=episode.podcast, subscriber=user)

        send_new_episodes_email(user)

        assert len(mailoutbox) == 1

    @pytest.mark.django_db()
    def test_not_subscribed(self, user, episode, mailoutbox):
        send_new_episodes_email(user)

        assert len(mailoutbox) == 0

    @pytest.mark.django_db()
    def test_no_other_recent_episodes(self, user, podcast, mailoutbox):
        SubscriptionFactory(podcast=podcast, subscriber=user)
        EpisodeFactory(podcast=podcast, pub_date=timezone.now() - timedelta(days=7))

        send_new_episodes_email(user)

        assert len(mailoutbox) == 0
