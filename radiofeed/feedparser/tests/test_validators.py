import pytest

from radiofeed.feedparser.validators import (
    duration,
    explicit,
    language,
    pg_integer,
    url,
)


class TestLanguage:
    def test_full_locale(self):
        assert language("en-US") == "en"

    def test_uppercase(self):
        assert language("FI") == "fi"


class TestExplicit:
    def test_true(self):
        assert explicit("yes") is True

    def test_false(self):
        assert explicit("no") is False

    def test_none(self):
        assert explicit(None) is False


class TestUrl:
    def test_ok(self):
        assert (
            url("http://yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_domain_only(self):
        assert (
            url("yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_bad_url(self):
        assert url("yhanewashington") is None

    def test_none(self):
        assert url(None) is None


class TestPgInteger:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(None, None, id="none"),
            pytest.param("100000000000000000000000", None, id="very large number"),
            pytest.param("1000", 1000, id="small number"),
            pytest.param("1000.50", None, id="float"),
            pytest.param("invalid", None, id="not a number"),
        ],
    )
    def test_pg_integer(self, value, expected):
        assert pg_integer(value) == expected


class TestDuration:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(None, "", id="none"),
            pytest.param("", "", id="empty"),
            pytest.param("invalid", "", id="invalid"),
            pytest.param("300", "300", id="seconds only"),
            pytest.param("10:30", "10:30", id="minutes and seconds"),
            pytest.param("10:30:59", "10:30:59", id="hours, minutes and seconds"),
            pytest.param("10:30:99", "10:30", id="hours, minutes and invalid seconds"),
        ],
    )
    def test_duration(self, value, expected):
        assert duration(value) == expected
