from radiofeed.podcasts.tasks import (
    feed_update,
    parse_itunes_feed,
    send_recommendations_email,
)


class TestTasks:
    def test_feed_update(self, mocker, podcast):
        patched = mocker.patch("radiofeed.podcasts.feed_updater.FeedUpdater")
        feed_update(podcast.id)
        patched.assert_called_with(podcast)

    def test_recommendations_email(self, mocker, user):
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        send_recommendations_email(user.id)
        patched.assert_called_with(user)

    def test_parse_itunes_feed(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.itunes.get_podcast_feed")
        parse_itunes_feed(12345)
        patched.assert_called_with(12345)
