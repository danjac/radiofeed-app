from datetime import timedelta

import pytest
from django.utils import timezone

from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.tests.factories import create_feed, create_item


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValueError, match=r"cannot be None"):
            Item(**create_item(pub_date=None))

    def test_pub_date_in_future(self):
        with pytest.raises(ValueError, match=r"cannot be in future"):
            Item(**create_item(pub_date=timezone.now() + timedelta(days=1)))

    def test_not_audio_mimetype(self):
        with pytest.raises(ValueError, match=r"'media_type' must be in"):
            Item(**create_item(media_type="video/mpeg"))

    def test_default_keywords_from_categories(self):
        item = Item(**create_item(), categories=["Gaming", "Hobbies", "Video Games"])
        assert item.keywords == "Gaming Hobbies Video Games"

    def test_defaults(self):
        item = Item(**create_item())
        assert item.explicit is False
        assert item.episode_type == "full"
        assert item.categories == []
        assert item.keywords == ""


class TestFeed:
    @pytest.fixture()
    def item(self):
        return Item(**create_item())

    def test_language(self, item):
        feed = Feed(
            **create_feed(),
            language="fr-CA",
            items=[item],
        )
        assert feed.language == "fr"

    def test_no_items(self):
        with pytest.raises(ValueError, match=r"max\(\) arg is an empty sequence"):
            Feed(**create_feed(), items=[])

    def test_not_complete(self, item):
        feed = Feed(
            **create_feed(),
            items=[item],
            complete="no",
        )

        assert feed.complete is False

    def test_complete(self, item):
        feed = Feed(
            **create_feed(),
            items=[item],
            complete="yes",
        )

        assert feed.complete is True

    def test_defaults(self, item):
        feed = Feed(
            **create_feed(),
            items=[item],
        )

        assert feed.complete is False
        assert feed.explicit is False
        assert feed.language == "en"
        assert feed.description == ""
        assert feed.categories == []
        assert feed.pub_date == item.pub_date
