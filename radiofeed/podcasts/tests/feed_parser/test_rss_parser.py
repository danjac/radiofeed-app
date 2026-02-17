import pathlib

import pytest

<<<<<<<< HEAD:radiofeed/podcasts/tests/feed_parser/test_rss_parser.py
<<<<<<<< HEAD:radiofeed/podcasts/tests/feed_parser/test_rss_parser.py
from radiofeed.podcasts.feed_parser.exceptions import InvalidRSSError
from radiofeed.podcasts.feed_parser.rss_parser import parse_rss
========
from radiofeed.parsers.feeds.exceptions import InvalidRSSError
from radiofeed.parsers.feeds.rss.parser import parse_rss
>>>>>>>> f7f200b02 (refactor: reorganise parsers):radiofeed/parsers/feeds/rss/tests/test_parser.py
========
from radiofeed.podcasts.parsers.feed_parser.exceptions import InvalidRSSError
from radiofeed.podcasts.parsers.rss_parser import parse_rss
>>>>>>>> f991ea3c0 (refactor: move parsers package to podcasts):radiofeed/podcasts/parsers/rss_parser/tests/test_parser.py


class TestParseRss:
    def read_mock_file(self, mock_filename):
        return (
            pathlib.Path(__file__).parents[2] / "tests" / "mocks" / mock_filename
        ).read_bytes()

    def test_empty(self):
        with pytest.raises(InvalidRSSError):
            parse_rss(b"")

    def test_invalid_xml(self):
        with pytest.raises(InvalidRSSError):
            parse_rss(b"junk string")

    def test_missing_channel(self):
        with pytest.raises(InvalidRSSError):
            parse_rss(b"<rss />")

    def test_invalid_feed_channel(self):
        with pytest.raises(InvalidRSSError):
            parse_rss(b"<rss><channel /></rss>")

    def test_with_bad_chars(self):
        content = self.read_mock_file("rss_mock.xml").decode("utf-8")
        content = content.replace("&amp;", "&")
        feed = parse_rss(bytes(content.encode("utf-8")))

        assert len(feed.items) == 20
        assert feed.title == "Mysterious Universe"

    @pytest.mark.parametrize(
        ("filename", "title", "num_items"),
        [
            pytest.param(
                "rss_mock.xml",
                "Mysterious Universe",
                20,
                id="default XML content",
            ),
            pytest.param(
                "rss_mock_large.xml",
                "AAA United Public Radio & UFO Paranormal Radio Network",
                8641,
                id="large XML content",
            ),
            pytest.param(
                "rss_mock_small.xml",
                "ABC News Update",
                1,
                id="small XML content",
            ),
            pytest.param(
                "rss_superfeedr.xml",
                "The Chuck ToddCast: Meet the Press",
                296,
                id="Superfeedr XML",
            ),
            pytest.param(
                "rss_missing_enc_length.xml",
                "The Vanilla JS Podcast",
                71,
                id="missing enclosure length",
            ),
            pytest.param(
                "rss_bad_urls.xml",
                "1972",
                3,
                id="bad urls",
            ),
            pytest.param(
                "rss_bad_pub_date.xml",
                "Old Time Radio Mystery Theater",
                69,
                id="invalid pub date",
            ),
            pytest.param(
                "rss_invalid_duration.xml",
                "At The Races with Steve Byk",
                450,
                id="invalid duration",
            ),
            pytest.param(
                "rss_bad_cover_urls.xml",
                "TED Talks Daily",
                327,
                id="invalid image URLs",
            ),
        ],
    )
    def test_parse_rss(self, filename, title, num_items):
        feed = parse_rss(self.read_mock_file(filename))
        assert feed.title == title
        assert len(feed.items) == num_items
