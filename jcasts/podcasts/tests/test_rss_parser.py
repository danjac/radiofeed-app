import pathlib

from datetime import timedelta

import pytest

from django.utils import timezone
from pydantic import ValidationError

from jcasts.podcasts.factories import FeedFactory, ItemFactory
from jcasts.podcasts.rss_parser import Feed, Item, RssParserError, parse_rss


class TestRssParser:
    def test_empty(self):
        with pytest.raises(RssParserError):
            parse_rss(b"")

    def test_invalid_xml(self):
        with pytest.raises(RssParserError):
            parse_rss(b"junk string")

    def test_missing_channel(self):
        with pytest.raises(RssParserError):
            parse_rss(b"<rss />")

    def test_invalid_feed_channel(self):
        with pytest.raises(RssParserError):
            parse_rss(b"<rss><channel /></rss>")

    def test_missing_enclosure_length(self):

        feed, items = self.parse_rss_from_mock_file("rss_missing_enc_length.xml")
        assert feed.title == "The Vanilla JS Podcast"
        assert len(items) == 71

    def test_with_bad_chars(self):
        content = self.read_mock_file("rss_mock.xml").decode("utf-8")
        content = content.replace("&amp;", "&")
        feed, items = parse_rss(bytes(content.encode("utf-8")))

        assert len(items) == 20
        assert feed.title == "Mysterious Universe"

    def test_unicode_errors(self):
        feed, items = self.parse_rss_from_mock_file("rss_mock_large.xml")
        assert feed.title == "AAA United Public Radio & UFO Paranormal Radio Network"
        assert len(items) == 8641

    def test_iso_8859_1(self):
        feed, items = self.parse_rss_from_mock_file("rss_mock_iso_8859-1.xml")
        assert feed.title == "Thunder & Lightning"
        assert len(items) == 643

    def test_owner_missing(self):
        feed, items = self.parse_rss_from_mock_file("rss_mock_small.xml")

        assert len(items) == 1
        assert feed.title == "ABC News Update"

    def test_ok(self):
        feed, items = self.parse_rss_from_mock_file("rss_mock.xml")

        assert len(items) == 20
        assert feed.title == "Mysterious Universe"

    def read_mock_file(self, mock_filename):
        return open(
            pathlib.Path(__file__).parent / "mocks" / mock_filename,
            "rb",
        ).read()

    def parse_rss_from_mock_file(self, mock_filename):
        return parse_rss(self.read_mock_file(mock_filename))


class TestFeed:
    def test_ok(self):
        feed = Feed.parse_obj(FeedFactory())
        assert not feed.explicit

    def test_empty_link(self):
        feed = Feed.parse_obj(FeedFactory(link=""))
        assert feed.link == ""

    def test_missing_title(self):
        with pytest.raises(ValidationError):
            Feed.parse_obj(FeedFactory(title=None))

    def test_explicit_true(self):
        feed = Feed.parse_obj(FeedFactory(explicit="yes"))
        assert feed.explicit

    def test_explicit_false(self):
        feed = Feed.parse_obj(FeedFactory(explicit="no"))
        assert not feed.explicit


class TestItem:
    def test_ok(self):
        item = Item.parse_obj(ItemFactory())
        assert not item.explicit

    def test_not_audio(self):
        with pytest.raises(ValidationError):
            Item.parse_obj(ItemFactory(media_type="video/mp4"))

    def test_pub_date_none(self):
        with pytest.raises(ValidationError):
            Item.parse_obj(ItemFactory(pub_date=None))

    def test_pub_date_gt_now(self):
        with pytest.raises(ValidationError):
            Item.parse_obj(
                ItemFactory(pub_date=(timezone.now() + timedelta(days=3)).isoformat())
            )

    def test_explicit_true(self):
        item = Item.parse_obj(ItemFactory(explicit="yes"))
        assert item.explicit

    def test_explicit_false(self):
        item = Item.parse_obj(ItemFactory(explicit="no"))
        assert not item.explicit
