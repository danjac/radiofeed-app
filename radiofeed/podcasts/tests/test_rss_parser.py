import pathlib

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers.rss_parser import (
    RssParserError,
    parse_audio,
    parse_duration,
    parse_explicit,
    parse_int,
    parse_pub_date,
    parse_rss,
    parse_url,
)


class TestConverters:
    def test_parse_pub_date_is_not_date(self):
        with pytest.raises(ValueError):
            parse_pub_date("test")

    def test_parse_pub_date_is_invalid_date(self):
        with pytest.raises(ValueError):
            parse_pub_date("Sun, 28 Apr 2013 15:12:352 CST")

    def test_parse_pub_date_is_future(self):
        with pytest.raises(ValueError):
            parse_pub_date((timezone.now() + timedelta(days=3)).strftime("%c"))

    def test_parse_pub_date_is_valid(self):
        assert parse_pub_date("Fri, 19 Jun 2020 16:58:03 +0000")

    @pytest.mark.parametrize(
        "value,raises",
        [
            ("", True),
            ("video/mp4", True),
            ("audio/mp3", False),
        ],
    )
    def test_parse_audio(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                parse_audio(value)
        else:
            assert parse_audio(value) == value

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", ""),
            ("invalid", ""),
            ("300", "300"),
            ("10:30", "10:30"),
            ("10:30:59", "10:30:59"),
            ("10:30:99", "10:30"),
        ],
    )
    def test_parse_duration(self, value, expected):
        assert parse_duration(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1234", 1234),
            ("0", 0),
            ("-111111111111111", None),
            ("111111111111111", None),
            ("", None),
            ("a string", None),
        ],
    )
    def test_parse_int(self, value, expected):
        assert parse_int(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("http://example.com", "http://example.com"),
            ("example", None),
            (None, None),
        ],
    )
    def test_parse_url(self, value, expected):
        assert parse_url(value) == expected

    @pytest.mark.parametrize(
        "value,raises",
        [
            ("http://example.com", False),
            ("example", True),
            ("", True),
        ],
    )
    def test_parse_url_raises(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                parse_url(value, raises=True)
        else:
            assert parse_url(value, raises=True) == value

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("clean", True),
            ("yes", True),
            ("no", False),
            ("", False),
        ],
    )
    def test_parse_explicit(self, value, expected):
        assert parse_explicit(value) is expected


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
                "rss_bad_pub_date.xml",
                "Old Time Radio Mystery Theater",
                69,
            ),
            (
                "rss_mock_large.xml",
                "AAA United Public Radio & UFO Paranormal Radio Network",
                8641,
            ),
            ("rss_mock_iso_8859-1.xml", "Thunder & Lightning", 643),
            (
                "rss_mock_small.xml",
                "ABC News Update",
                1,
            ),
            (
                "rss_mock.xml",
                "Mysterious Universe",
                20,
            ),
            ("rss_invalid_duration.xml", "At The Races with Steve Byk", 450),
            (
                "rss_bad_cover_urls.xml",
                "TED Talks Daily",
                327,
            ),
            (
                "rss_superfeedr.xml",
                "The Chuck ToddCast: Meet the Press",
                296,
            ),
        ],
    )
    def test_parse_rss(self, filename, title, num_items):
        feed, items = parse_rss(self.read_mock_file(filename))
        assert feed.title == title
        assert len(items) == num_items

    def read_mock_file(self, mock_filename):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()
