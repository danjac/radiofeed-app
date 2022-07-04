from django.core.management import call_command

from radiofeed.podcasts.factories import RecommendationFactory
from radiofeed.podcasts.itunes import Feed


class TestRecommender:
    def test_create_recommendations(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )
        call_command("recommender")
        patched.assert_called()

    def test_send_emails(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.tasks.send_recommendations_email.map"
        )
        call_command("recommender", email=True)
        patched.assert_called()


class TestItunesCrawler:
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
        call_command("itunes_crawler")
        patched.assert_called()
