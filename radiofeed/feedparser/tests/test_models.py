from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.feedparser.models import Feed, Item


@pytest.fixture
def item_dict():
    return {
        "guid": "test",
        "title": "test",
        "media_url": "https://example.com/",
        "media_type": "audio/mpeg",
        "pub_date": timezone.now() - timedelta(days=1),
    }


class TestItem:
    def test_pub_date_none(self, item_dict):
        with pytest.raises(ValueError):
            Item(**item_dict | {"pub_date": None})

    def test_pub_date_in_future(self, item_dict):
        with pytest.raises(ValueError):
            Item(**item_dict | {"pub_date": timezone.now() + timedelta(days=1)})

    def test_not_audio_mimetype(self, item_dict):
        with pytest.raises(ValueError):
            Item(**item_dict | {"media_type": "video/mpeg"})

    def test_default_keywords_from_categories(self, item_dict):
        item = Item(**item_dict, categories=["Gaming", "Hobbies", "Video Games"])
        assert item.keywords == "Gaming Hobbies Video Games"

    def test_defaults(self, item_dict):
        item = Item(**item_dict)
        assert item.explicit is False
        assert item.episode_type == "full"
        assert item.categories == []
        assert item.keywords == ""


class TestFeed:
    @pytest.fixture
    def item(self, item_dict):
        return Item(**item_dict)

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
