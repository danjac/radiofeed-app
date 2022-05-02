from datetime import timedelta

from podtracker.episodes.emails import send_new_episodes_email, send_new_episodes_emails
from podtracker.episodes.factories import EpisodeFactory
from podtracker.podcasts.factories import SubscriptionFactory
from podtracker.users.factories import UserFactory


class TestSendNewEpisodesEmails:
    def test_command(self, db, mocker):

        yes = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)
        UserFactory(send_email_notifications=True, is_active=False)

        mock_send = mocker.patch(
            "podtracker.episodes.emails.send_new_episodes_email.delay"
        )

        send_new_episodes_emails()

        assert len(mock_send.mock_calls) == 1
        assert mock_send.call_args == (
            (
                yes,
                timedelta(days=7),
            ),
        )


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
