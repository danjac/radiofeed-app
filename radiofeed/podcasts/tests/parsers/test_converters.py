import pytest

from radiofeed.podcasts.parsers import converters


class TestComplete:
    def test_true(self):
        assert converters.complete("yes") is True

    def test_false(self):
        assert converters.complete("no") is False

    def test_none(self):
        assert converters.complete(None) is False


class TestExplicit:
    def test_true(self):
        assert converters.explicit("yes") is True

    def test_false(self):
        assert converters.explicit("no") is False

    def test_none(self):
        assert converters.explicit(None) is False


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
        assert converters.duration(value) == expected


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
        assert converters.language_code(value) == expected
