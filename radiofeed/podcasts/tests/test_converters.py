from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers import converters


class TestPubDate:
    def test_not_date(self):
        with pytest.raises(ValueError):
            converters.pub_date("test")

    def test_invalid_date(self):
        with pytest.raises(ValueError):
            converters.pub_date("Sun, 28 Apr 2013 15:12:352 CST")

    def test_in_future(self):
        with pytest.raises(ValueError):
            converters.pub_date((timezone.now() + timedelta(days=3)).strftime("%c"))

    def test_ok(self):
        assert converters.pub_date("Fri, 19 Jun 2020 16:58:03 +0000")


class TestAudio:
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
                converters.audio(value)
        else:
            assert converters.audio(value) == value


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
        assert converters.duration(value) == expected


class TestInteger:
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
    def test_integer(self, value, expected):
        assert converters.integer(value) == expected


class TestUrl:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("http://example.com", "http://example.com"),
            ("example", None),
            (None, None),
        ],
    )
    def test_parse_url(self, value, expected):
        assert converters.url(value) == expected

    @pytest.mark.parametrize(
        "value,raises",
        [
            ("http://example.com", False),
            ("example", True),
            ("", True),
        ],
    )
    def test_raises(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                converters.url(value, raises=True)
        else:
            assert converters.url(value, raises=True) == value


class TestExplicit:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("clean", True),
            ("yes", True),
            ("no", False),
            ("", False),
        ],
    )
    def test_explicit(self, value, expected):
        assert converters.explicit(value) is expected
