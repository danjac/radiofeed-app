import uuid

from datetime import timedelta

from django.utils import timezone

from radiofeed.podcasts.parsers.models import Feed, Item


class TestFeed:
    def test_single_pub_date(self):
        now = timezone.now()
        feed = Feed(
            title="test",
            language="en",
            complete=False,
            explicit=False,
            link="",
            cover_url="",
            funding_url="",
            items=[
                Item(
                    title="test",
                    pub_date=now,
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                    cover_url="",
                    duration="",
                )
            ],
        )
        assert feed.pub_date == now

    def test_multiple_pub_dates(self):
        now = timezone.now()

        feed = Feed(
            title="test",
            language="en",
            link="",
            complete=False,
            explicit=False,
            cover_url="",
            funding_url="",
            items=[
                Item(
                    title="test 1",
                    pub_date=now,
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                    cover_url="",
                    duration="",
                ),
                Item(
                    title="test 2",
                    pub_date=now - timedelta(days=3),
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                    cover_url="",
                    duration="",
                ),
            ],
        )
        assert feed.pub_date == now
