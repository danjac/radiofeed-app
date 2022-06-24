import pytest

from radiofeed.podcasts.parsers.converters import duration, int_or_none, language_code


class TestIntOrNone:
    def test_is_none(self):
        assert int_or_none(None) is None

    def test_is_empty(self):
        assert int_or_none("") is None

    def test_is_number(self):
        assert int_or_none("11111") == 11111


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
