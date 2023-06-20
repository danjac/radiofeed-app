import pytest

from radiofeed.feedparser import converters


class TestLanguage:
    def test_full_locale(self):
        assert converters.language("en-US") == "en"

    def test_uppercase(self):
        assert converters.language("FI") == "fi"


class TestExplicit:
    def test_true(self):
        assert converters.explicit("yes") is True

    def test_false(self):
        assert converters.explicit("no") is False

    def test_none(self):
        assert converters.explicit(None) is False


class TestUrl:
    def test_ok(self):
        assert (
            converters.url("http://yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_domain_only(self):
        assert (
            converters.url("yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_bad_url(self):
        assert converters.url("yhanewashington") is None

    def test_none(self):
        assert converters.url(None) is None


class TestDuration:
    @pytest.mark.parametrize(
        ("value", "expected"),
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
