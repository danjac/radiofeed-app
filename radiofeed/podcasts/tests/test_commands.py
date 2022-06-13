import pathlib

from django.core.management import call_command

from radiofeed.podcasts.itunes import Feed
from radiofeed.podcasts.models import Podcast
from radiofeed.users.factories import UserFactory


class TestCreateRecommendations:
    def test_command(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.recommender.recommend")
        call_command("create_recommendations")
        patched.assert_called()


class TestCrawlItunes:
    def test_command(self, mocker, podcast):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.crawl",
            return_value=[
                Feed(
                    title="test 1",
                    url="https://example1.com",
                    rss="https://example1.com/test.xml",
                ),
                Feed(
                    title="test 2",
                    url="https://example2.com",
                    rss=podcast.rss,
                    podcast=podcast,
                ),
            ],
        )
        call_command("crawl_itunes")
        patched.assert_called()


class TestImportPodcasts:
    def test_command(self, db):
        call_command(
            "import_podcasts",
            pathlib.Path(__file__).parent / "mocks" / "feeds.txt",
        )

        assert Podcast.objects.count() == 18


class TestExportPodcasts:
    def test_command(self, mocker, podcast):
        mocker.patch("builtins.open")
        mock_writer = mocker.Mock()
        mocker.patch("csv.writer", return_value=mock_writer)
        call_command("export_podcasts", "filename.txt")
        mock_writer.writerow.assert_called_with([podcast.rss])


class TestSendRecommendationsEmails:
    def test_command(self, db, mocker):
        user = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)

        patched = mocker.patch(
            "radiofeed.podcasts.emails.send_recommendations_email.delay"
        )

        call_command("send_recommendation_emails")
        patched.assert_called_with(user.id)


class TestFeedUpdate:
    def test_command(self, mocker):

        patched = mocker.patch(
            "radiofeed.podcasts.feed_updater.schedule_podcast_feeds_for_update",
        )
        mocker.patch("multiprocessing.cpu_count", return_value=4)

        call_command("feed_update")

        patched.assert_called_with(400, job_timeout=360)
