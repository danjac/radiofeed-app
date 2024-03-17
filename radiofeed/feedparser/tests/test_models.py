from datetime import timedelta

import pytest
from django.utils import timezone
from pydantic import ValidationError

from radiofeed.feedparser.models import Feed, Item, duration, explicit, language, url
from radiofeed.feedparser.tests.factories import create_feed, create_item


class TestLanguage:
    def test_full_locale(self):
        assert language("en-US") == "en"

    def test_uppercase(self):
        assert language("FI") == "fi"


class TestExplicit:
    def test_true(self):
        assert explicit("yes") is True

    def test_false(self):
        assert explicit("no") is False

    def test_none(self):
        assert explicit(None) is False


class TestUrl:
    def test_ok(self):
        assert (
            url("http://yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_domain_only(self):
        assert (
            url("yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_bad_url(self):
        assert url("yhanewashington") is None

    def test_none(self):
        assert url(None) is None


class TestDuration:
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
    def test_parse_duration(self, value, expected):
        assert duration(value) == expected


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValidationError):
            Item(**create_item(pub_date=None))

    def test_pub_date_in_future(self):
        with pytest.raises(ValidationError):
            Item(**create_item(pub_date=timezone.now() + timedelta(days=1)))

    def test_not_audio_mimetype(self):
        with pytest.raises(ValidationError):
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
