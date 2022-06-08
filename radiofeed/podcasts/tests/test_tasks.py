from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import (
    parse_podcast_feed,
    parse_podcast_feeds,
    recommend,
    send_recommendations_email,
    send_recommendations_emails,
)
from radiofeed.users.factories import UserFactory


class TestTasks:
    def test_parse_podcast_feeds(self, mocker, podcast):

        mocker.patch(
            "radiofeed.podcasts.scheduler.schedule_podcast_feeds",
            return_value=Podcast.objects.all(),
        )

        patched = mocker.patch("radiofeed.podcasts.tasks.parse_podcast_feed.map")

        parse_podcast_feeds()

        calls = list(patched.mock_calls[0][1][0])
        assert calls == [(podcast.id,)]

    def test_parse_podcast_feed(self, podcast, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.feed_parser.parse_podcast_feed"
        )
        parse_podcast_feed(podcast.id)
        patched.assert_called_with(podcast)

    def test_parse_podcast_feed_podcast_not_found(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.feed_parser.parse_podcast_feed"
        )
        parse_podcast_feed(1234)
        patched.assert_not_called()

    def test_send_recommendations_email(self, mocker, user):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.emails.send_recommendations_email"
        )
        send_recommendations_email(user.id)
        patched.assert_called_with(user)

    def test_send_recommendations_email_user_not_found(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.emails.send_recommendations_email"
        )
        send_recommendations_email(1234)
        patched.assert_not_called()

    def test_recommend(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.tasks.recommender.recommend")
        recommend()
        patched.assert_called()

    def test_send_recommendations_emails(self, db, mocker):
        user = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)

        patched = mocker.patch(
            "radiofeed.podcasts.tasks.send_recommendations_email.map"
        )

        send_recommendations_emails()
        assert list(patched.mock_calls[0][1][0]) == [(user.id,)]
