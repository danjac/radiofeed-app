import pytest

from ..templatetags.episodes import format_duration

pytestmark = pytest.mark.django_db


class TestFormatDuration:
    def test_format_duration_if_empty(self):
        assert format_duration(None) == ""
        assert format_duration("0") == ""
        assert format_duration("") == ""

    def test_format_duration_if_less_than_one_minute(self):
        assert format_duration("30") == "<1min"

    def test_format_duration_if_less_than_one_hour(self):
        assert format_duration("2400") == "40min"

    def test_format_duration_if_more_than_one_hour(self):
        assert format_duration("9000") == "2h 30min"
