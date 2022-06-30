import pathlib

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts import feed_parser


class TestExplicit:
    def test_true(self):
        assert feed_parser.explicit("yes") is True

    def test_false(self):
        assert feed_parser.explicit("no") is False

    def test_none(self):
        assert feed_parser.explicit(None) is False


class TestDuration:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("invalid", ""),
            ("300", "300"),
            ("10:30", "10:30"),
            ("10:30:59", "10:30:59"),
            ("10:30:99", "10:30"),
        ],
    )
    def test_parse_duration(self, value, expected):
        assert feed_parser.duration(value) == expected


class TestNotEmpty:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("ok", False),
            ("", True),
            (None, True),
        ],
    )
    def test_required(self, value, raises):

        if raises:
            with pytest.raises(ValueError):
                feed_parser.required(None, None, value)
        else:
            feed_parser.required(None, None, value)


class TestUrl:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("http://example.com", False),
            ("https://example.com", False),
            ("example", True),
        ],
    )
    def test_url(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                feed_parser.url(None, None, value)
        else:
            feed_parser.url(None, None, value)


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValueError):
            feed_parser.Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="audio/mpeg",
                pub_date=None,
            )

    def test_pub_date_in_future(self):
        with pytest.raises(ValueError):
            feed_parser.Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="audio/mpeg",
                pub_date=timezone.now() + timedelta(days=1),
            )

    def test_not_audio_mimetype(self):
        with pytest.raises(ValueError):
            feed_parser.Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="video/mpeg",
                pub_date=timezone.now() - timedelta(days=1),
            )

    def test_defaults(self):
        item = feed_parser.Item(
            guid="test",
            title="test",
            media_url="https://example.com/",
            media_type="audio/mpeg",
            pub_date=timezone.now() - timedelta(days=1),
        )

        assert item.explicit is False
        assert item.episode_type == "full"


class TestFeed:
    @pytest.fixture
    def item(self):
        return feed_parser.Item(
            guid="test",
            title="test",
            media_url="https://example.com/",
            media_type="audio/mpeg",
            pub_date=timezone.now() - timedelta(days=1),
        )

    def test_language(self, item):
        feed = feed_parser.Feed(
            title="test",
            language="fr-CA",
            items=[item],
        )
        assert feed.language == "fr"

    def test_no_items(self):
        with pytest.raises(ValueError):
            feed_parser.Feed(
                title="test",
                items=[],
            )

    def test_not_complete(self, item):
        feed = feed_parser.Feed(
            title="test",
            items=[item],
            complete="no",
        )

        assert feed.complete is False

    def test_complete(self, item):
        feed = feed_parser.Feed(
            title="test",
            items=[item],
            complete="yes",
        )

        assert feed.complete is True

    def test_defaults(self, item):
        feed = feed_parser.Feed(
            title="test",
            items=[item],
        )

        assert feed.complete is False
        assert feed.explicit is False
        assert feed.language == "en"
        assert feed.description == ""
        assert feed.categories == []
        assert feed.pub_date == item.pub_date


class TestFeedParser:
    def read_mock_file(self, mock_filename):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    def test_empty(self):
        with pytest.raises(feed_parser.FeedParserError):
            feed_parser.parse_feed(b"")

    def test_invalid_xml(self):
        with pytest.raises(feed_parser.FeedParserError):
            feed_parser.parse_feed(b"junk string")

    def test_missing_channel(self):
        with pytest.raises(feed_parser.FeedParserError):
            feed_parser.parse_feed(b"<rss />")

    def test_invalid_feed_channel(self):
        with pytest.raises(feed_parser.FeedParserError):
            feed_parser.parse_feed(b"<rss><channel /></rss>")

    def test_with_bad_chars(self):
        content = self.read_mock_file("rss_mock.xml").decode("utf-8")
        content = content.replace("&amp;", "&")
        feed = feed_parser.parse_feed(bytes(content.encode("utf-8")))

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
    def test_parse_feed(self, filename, title, num_items):
        feed = feed_parser.parse_feed(self.read_mock_file(filename))
        assert feed.title == title
        assert len(feed.items) == num_items
