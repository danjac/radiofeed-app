import pathlib

from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts.factories import FeedFactory, ItemFactory
from jcasts.podcasts.rss_parser import (
    Feed,
    Item,
    RssParserError,
    duration,
    int_or_none,
    is_explicit,
    is_url,
    not_empty,
    parse_rss,
    url_or_none,
)


class TestConverters:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("invalid", ""),
            ("300", "300"),
            ("10:30", "10:30"),
            ("10:30:59", "10:30:59"),
            ("10:30:99", "10:30"),
        ],
    )
    def test_duration(self, value, expected):
        assert duration(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1234", 1234),
            (None, None),
            ("integer", None),
        ],
    )
    def test_int_or_none(self, value, expected):
        assert int_or_none(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("http://example.com", "http://example.com"),
            ("example", None),
            (None, None),
        ],
    )
    def test_url_or_none(self, value, expected):
        assert url_or_none(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("clean", True),
            ("yes", True),
            ("no", False),
            (None, False),
        ],
    )
    def test_is_explicit(self, value, expected):
        assert is_explicit(value) is expected


class TestValidators:
    @pytest.mark.parametrize(
        "value,exc",
        [
            (None, ValueError),
            ("example", ValueError),
            ("ftp://example.com", ValueError),
            ("http://example.com", None),
            ("https://example.com", None),
        ],
    )
    def test_is_url(self, value, exc):
        if exc:
            with pytest.raises(exc):
                is_url(None, "url", None)
        else:
            is_url(None, "url", value)

    @pytest.mark.parametrize(
        "value,exc",
        [
            (None, ValueError),
            (False, ValueError),
            ("", ValueError),
            ("ok", None),
        ],
    )
    def test_not_empty(self, value, exc):
        if exc:
            with pytest.raises(exc):
                not_empty(None, "url", None)
        else:
            not_empty(None, "url", value)


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

    def test_with_bad_chars(self):
        content = self.read_mock_file("rss_mock.xml").decode("utf-8")
        content = content.replace("&amp;", "&")
        feed, items = parse_rss(bytes(content.encode("utf-8")))

        assert len(items) == 20
        assert feed.title == "Mysterious Universe"

    @pytest.mark.parametrize(
        "filename,title,num_items",
        [
            ("rss_missing_enc_length.xml", "The Vanilla JS Podcast", 71),
            (
                "rss_mock_large.xml",
                "AAA United Public Radio & UFO Paranormal Radio Network",
                8641,
            ),
            ("rss_mock_iso_8859-1.xml", "Thunder & Lightning", 643),
            ("rss_mock_small.xml", "ABC News Update", 1),
            ("rss_mock.xml", "Mysterious Universe", 20),
            ("rss_invalid_duration.xml", "At The Races with Steve Byk", 450),
            ("rss_bad_cover_urls.xml", "TED Talks Daily", 327),
        ],
    )
    def test_parse_rss(self, filename, title, num_items):
        feed, items = parse_rss(self.read_mock_file(filename))
        assert feed.title == title
        assert len(items) == num_items

    def read_mock_file(self, mock_filename):
        return open(
            pathlib.Path(__file__).parent / "mocks" / mock_filename,
            "rb",
        ).read()


class TestFeed:
    def test_ok(self):
        Feed(**FeedFactory())

    def test_empty_link(self):
        feed = Feed(**FeedFactory(link=""))
        assert feed.link is None

    def test_missing_title(self):
        with pytest.raises(ValueError):
            Feed(**FeedFactory(title=None))

    def test_explicit_true(self):
        feed = Feed(**FeedFactory(explicit="yes"))
        assert feed.explicit

    def test_explicit_false(self):
        feed = Feed(**FeedFactory(explicit="no"))
        assert not feed.explicit


class TestItem:
    def test_ok(self):
        item = Item(**ItemFactory())
        assert not item.explicit

    def test_not_audio(self):
        with pytest.raises(ValueError):
            Item(**ItemFactory(media_type="video/mp4"))

    def test_pub_date_none(self):
        with pytest.raises(ValueError):
            Item(**ItemFactory(pub_date=None))

    def test_pub_date_gt_now(self):
        with pytest.raises(ValueError):
            Item(
                **ItemFactory(pub_date=(timezone.now() + timedelta(days=3)).isoformat())
            )

    def test_explicit_true(self):
        item = Item(**ItemFactory(explicit="yes"))
        assert item.explicit

    def test_explicit_false(self):
        item = Item(**ItemFactory(explicit="no"))
        assert not item.explicit

    def test_empty_duration(self):
        item = Item(**ItemFactory(duration=""))
        assert item.duration == ""

    def test_invalid_duration(self):
        item = Item(**ItemFactory(duration="https://example.com"))
        assert item.duration == ""

    def test_duration_seconds_only(self):
        item = Item(**ItemFactory(duration="1000"))
        assert item.duration == "1000"

    def test_duration_h_m(self):
        item = Item(**ItemFactory(duration="10:20"))
        assert item.duration == "10:20"

    def test_duration_h_m_over_60(self):
        item = Item(**ItemFactory(duration="10:90"))
        assert item.duration == "10"

    def test_duration_h_m_s(self):
        item = Item(**ItemFactory(duration="10:30:30"))
        assert item.duration == "10:30:30"
