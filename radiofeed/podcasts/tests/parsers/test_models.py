import uuid

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers.models import (
    Feed,
    Item,
    duration,
    int_in_range,
    language_code,
    min_len,
    pub_date,
    url,
)


class TestUrl:
    @pytest.mark.parametrize(
        "value,expected,raises",
        [
            ("http://example.com", "http://example.com", False),
            ("https://example.com", "https://example.com", False),
            (None, None, False),
            ("example", None, True),
        ],
    )
    def test_url(self, value, expected, raises):
        if raises:
            with pytest.raises(ValueError):
                url(None, None, value)
        else:
            url(None, None, value)


class TestFeed:
    def test_single_pub_date(self):
        now = timezone.now()
        feed = Feed(
            title="test",
            language="en",
            items=[
                Item(
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

        feed = Feed(
            title="test",
            language="en",
            items=[
                Item(
                    title="test 1",
                    pub_date=now,
                    media_url="",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                ),
                Item(
                    title="test 2",
                    pub_date=now - timedelta(days=3),
                    media_url="",
                    media_type="audio/mpeg",
                    guid=uuid.uuid4().hex,
                ),
            ],
        )
        assert feed.latest_pub_date == now


class TestDuration:
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
        assert duration(value) == expected


class TestLanguageCode:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("fr", "fr"),
            ("fr-CA", "fr"),
            ("", "en"),
        ],
    )
    def test_language_code(self, value, expected):
        assert language_code(value) == expected


class TestIntInRange:
    def test_too_low(self):
        with pytest.raises(ValueError):
            int_in_range(None, None, -2147483649)

    def test_too_high(self):
        with pytest.raises(ValueError):
            int_in_range(None, None, 2147483649)

    def test_ok(self):
        int_in_range(None, None, 1000)


class TestPubDate:
    def test_ok(self):
        pub_date(None, None, timezone.now() - timedelta(hours=1))

    def test_in_future(self):
        with pytest.raises(ValueError):
            pub_date(None, None, timezone.now() + timedelta(hours=1))


class TestMinLen:
    def test_ok(self):
        min_len(3)(None, None, [1, 2, 3])

    def test_too_small(self):
        with pytest.raises(ValueError):
            min_len(5)(None, None, [1, 2, 3])
