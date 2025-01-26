from datetime import timedelta

import pytest
from django.utils import timezone
from pydantic import ValidationError

from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.tests.factories import FeedFactory, ItemFactory


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValidationError):
            Item(**ItemFactory(pub_date=None))

    def test_pub_date_in_future(self):
        with pytest.raises(ValidationError):
            Item(**ItemFactory(pub_date=timezone.now() + timedelta(days=1)))

    def test_pub_date_not_valid(self):
        with pytest.raises(ValidationError):
            Item(**ItemFactory(pub_date="a string"))

    def test_not_audio_mimetype(self):
        with pytest.raises(ValidationError):
            Item(**ItemFactory(media_type="video/mpeg"))

    def test_length_too_long(self):
        item = Item(**ItemFactory(length="3147483647"))
        assert item.length is None

    def test_length_invalid(self):
        item = Item(**ItemFactory(length="invalid"))
        assert item.length is None

    def test_length_valid(self):
        item = Item(**ItemFactory(length="1000"))
        assert item.length == 1000

    def test_default_keywords_from_categories(self):
        item = Item(**ItemFactory(categories=["Gaming", "Hobbies", "Video Games"]))
        assert set(item.keywords.split()) == {"gaming", "hobbies", "video", "games"}

    def test_defaults(self):
        item = Item(**ItemFactory())
        assert item.explicit is False
        assert item.episode_type == "full"
        assert item.categories == set()
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
        assert Item(**ItemFactory(duration=value)).duration == expected


class TestFeed:
    @pytest.fixture
    def item(self):
        return Item(**ItemFactory())

    def test_language(self, item):
        feed = Feed(**FeedFactory(language="fr-CA", items=[item]))
        assert feed.language == "fr"

    def test_language_empty(self, item):
        feed = Feed(**FeedFactory(language="", items=[item]))
        assert feed.language == "en"

    def test_language_none(self, item):
        feed = Feed(**FeedFactory(language=None, items=[item]))
        assert feed.language == "en"

    def test_no_items(self):
        with pytest.raises(ValidationError):
            Feed(**FeedFactory(items=[]))

    def test_not_complete(self, item):
        feed = Feed(**FeedFactory(items=[item], complete="no"))

        assert feed.complete is False

    def test_complete(self, item):
        feed = Feed(**FeedFactory(items=[item], complete="yes"))

        assert feed.complete is True

    def test_podcast_type_serial(self, item):
        feed = Feed(**FeedFactory(items=[item], podcast_type="serial"))
        assert feed.podcast_type == "serial"

    def test_podcast_type_is_none(self, item):
        feed = Feed(**FeedFactory(items=[item]))
        assert feed.podcast_type == "episodic"

    def test_defaults(self, item):
        feed = Feed(**FeedFactory(items=[item]))

        assert feed.complete is False
        assert feed.explicit is False
        assert feed.language == "en"
        assert feed.description == ""
        assert feed.categories == set()
        assert feed.pub_date == item.pub_date
