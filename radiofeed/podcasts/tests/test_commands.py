import pytest
from django.core.management import call_command

from radiofeed.podcasts.itunes import Feed
from radiofeed.podcasts.tests.factories import create_recommendation
from radiofeed.tests.factories import create_batch
from radiofeed.users.tests.factories import create_user


class TestCreateRecommendations:
    @pytest.mark.django_db()
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", create_batch(create_recommendation, 3)),
            ],
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendationsEmails:
    @pytest.mark.django_db()(transaction=True)
    def test_send_emails(self, mocker):
        create_user(send_email_notifications=True, is_active=True)
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        call_command("send_recommendations_emails")
        patched.assert_called()


class TestCrawlItunes:
    @pytest.mark.django_db()
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
