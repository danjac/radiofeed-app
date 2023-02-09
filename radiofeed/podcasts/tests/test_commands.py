from __future__ import annotations

from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from radiofeed.factories import create_batch
from radiofeed.podcasts.factories import create_podcast, create_recommendation
from radiofeed.podcasts.itunes import Feed
from radiofeed.users.factories import create_user


class TestSubscribeWebsubFeeds:
    hub = "https://example.com/hub/"
    topic = "https://example.com/topic/"

    @pytest.fixture
    def subscribe(self, mocker):
        return mocker.patch(
            "radiofeed.podcasts.subscriber.subscribe",
        )

    def test_not_requested(self, db, subscribe):
        create_podcast(websub_hub=self.hub, websub_topic=self.topic)
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_called()

    def test_not_websub(self, db, subscribe, podcast):
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_not_called()

    def test_expired_none(self, db, subscribe):
        now = timezone.now()
        create_podcast(
            websub_hub=self.hub,
            websub_topic=self.topic,
            websub_requested=now,
            websub_expires=None,
        )
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_not_called()

    def test_expired(self, db, subscribe):
        now = timezone.now()
        create_podcast(
            websub_hub=self.hub,
            websub_topic=self.topic,
            websub_requested=now,
            websub_expires=now - timedelta(days=1),
        )
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_called()

    def test_not_expired(self, db, subscribe):
        now = timezone.now()
        create_podcast(
            websub_hub=self.hub,
            websub_topic=self.topic,
            websub_requested=now,
            websub_expires=now + timedelta(days=1),
        )
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_not_called()


class TestCreateRecommendations:
    def test_create_recommendations(self, db, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", create_batch(create_recommendation, 3)),
            ],
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendationsEmails:
    def test_send_emails(self, db, mocker):
        create_user(send_email_notifications=True, is_active=True)
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        call_command("send_recommendations_emails")
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
