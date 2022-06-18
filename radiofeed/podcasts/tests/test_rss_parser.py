import pathlib
import uuid

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers import rss_parser


class TestFeed:
    @pytest.fixture
    def test_latest_pub_date_if_empty(self):
        assert rss_parser.Feed(title="test", language="en").latest_pub_date is None

    def test_single_pub_date(self):
        now = timezone.now()
        feed = rss_parser.Feed(
            title="test",
            language="en",
            items=[
                rss_parser.Item(
                    title="test",
                    pub_date=now,
                    media_url="",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                )
            ],
        )
        assert feed.latest_pub_date == now

    def test_multiple_pub_dates(self):
        now = timezone.now()

        feed = rss_parser.Feed(
            title="test",
            language="en",
            items=[
                rss_parser.Item(
                    title="test 1",
                    pub_date=now,
                    media_url="",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                ),
                rss_parser.Item(
                    title="test 2",
                    pub_date=now - timedelta(days=3),
                    media_url="",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                ),
            ],
        )
        assert feed.latest_pub_date == now


class TestRssParser:
    def read_mock_file(self, mock_filename):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    def test_empty(self):
        with pytest.raises(rss_parser.RssParserError):
            rss_parser.parse_rss(b"")

    def test_invalid_xml(self):
        with pytest.raises(rss_parser.RssParserError):
            rss_parser.parse_rss(b"junk string")

    def test_missing_channel(self):
        with pytest.raises(rss_parser.RssParserError):
            rss_parser.parse_rss(b"<rss />")

    def test_invalid_feed_channel(self):
        with pytest.raises(rss_parser.RssParserError):
            rss_parser.parse_rss(b"<rss><channel /></rss>")

    def test_with_bad_chars(self):
        content = self.read_mock_file("rss_mock.xml").decode("utf-8")
        content = content.replace("&amp;", "&")
        feed = rss_parser.parse_rss(bytes(content.encode("utf-8")))

        assert len(feed.items) == 20
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
        feed = rss_parser.parse_rss(self.read_mock_file(filename))
        assert feed.title == title
        assert len(feed.items) == num_items
