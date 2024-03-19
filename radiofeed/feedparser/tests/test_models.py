from datetime import timedelta

import pytest
from django.utils import timezone
from pydantic import ValidationError

from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.tests.factories import create_feed, create_item


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValidationError):
            Item(**create_item(pub_date=None))

    def test_pub_date_in_future(self):
        with pytest.raises(ValidationError):
            Item(**create_item(pub_date=timezone.now() + timedelta(days=1)))

    def test_pub_date_not_valid(self):
        with pytest.raises(ValidationError):
            Item(**create_item(pub_date="a string"))

    def test_not_audio_mimetype(self):
        with pytest.raises(ValidationError):
            Item(**create_item(media_type="video/mpeg"))

    def test_length_too_long(self):
        item = Item(**create_item(length="3147483647"))
        assert item.length is None

    def test_length_invalid(self):
        item = Item(**create_item(length="invalid"))
        assert item.length is None

    def test_length_valid(self):
        item = Item(**create_item(length="1000"))
        assert item.length == 1000

    def test_default_keywords_from_categories(self):
        item = Item(**create_item(), categories=["Gaming", "Hobbies", "Video Games"])
        assert item.keywords == "Gaming Hobbies Video Games"

    def test_defaults(self):
        item = Item(**create_item())
        assert item.explicit is False
        assert item.episode_type == "full"
        assert item.categories == []
        assert item.keywords == ""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(None, "", id="none"),
            pytest.param("", "", id="empty"),
            pytest.param("invalid", "", id="invalid"),
            pytest.param("300", "300", id="seconds only"),
            pytest.param("10:30", "10:30", id="minutes and seconds"),
            pytest.param("10:30:59", "10:30:59", id="hours, minutes and seconds"),
            pytest.param("10:30:99", "10:30", id="hours, minutes and invalid seconds"),
        ],
    )
    def test_duration(self, value, expected):
        assert Item(**create_item(), duration=value).duration == expected


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

    def test_language_empty(self, item):
        feed = Feed(**create_feed(language="", items=[item]))
        assert feed.language == "en"

    def test_language_none(self, item):
        feed = Feed(**create_feed(language=None, items=[item]))
        assert feed.language == "en"

    def test_no_items(self):
        with pytest.raises(ValidationError):
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
