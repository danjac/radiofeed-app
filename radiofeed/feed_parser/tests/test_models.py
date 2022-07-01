from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.feed_parser.models import Feed, Item


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValueError):
            Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="audio/mpeg",
                pub_date=None,
            )

    def test_pub_date_in_future(self):
        with pytest.raises(ValueError):
            Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="audio/mpeg",
                pub_date=timezone.now() + timedelta(days=1),
            )

    def test_not_audio_mimetype(self):
        with pytest.raises(ValueError):
            Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="video/mpeg",
                pub_date=timezone.now() - timedelta(days=1),
            )

    def test_defaults(self):
        item = Item(
            guid="test",
            title="test",
            media_url="https://example.com/",
            media_type="audio/mpeg",
            pub_date=timezone.now() - timedelta(days=1),
        )

        assert item.explicit is False
        assert item.episode_type == "full"


class TestFeed:
    @pytest.fixture
    def item(self):
        return Item(
            guid="test",
            title="test",
            media_url="https://example.com/",
            media_type="audio/mpeg",
            pub_date=timezone.now() - timedelta(days=1),
        )

    def test_language(self, item):
        feed = Feed(
            title="test",
            language="fr-CA",
            items=[item],
        )
        assert feed.language == "fr"

    def test_no_items(self):
        with pytest.raises(ValueError):
            Feed(
                title="test",
                items=[],
            )

    def test_not_complete(self, item):
        feed = Feed(
            title="test",
            items=[item],
            complete="no",
        )

        assert feed.complete is False

    def test_complete(self, item):
        feed = Feed(
            title="test",
            items=[item],
            complete="yes",
        )

        assert feed.complete is True

    def test_defaults(self, item):
        feed = Feed(
            title="test",
            items=[item],
        )

        assert feed.complete is False
        assert feed.explicit is False
        assert feed.language == "en"
        assert feed.description == ""
        assert feed.categories == []
        assert feed.pub_date == item.pub_date
