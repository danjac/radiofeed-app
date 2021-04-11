from ..utils import duration_in_seconds, format_duration


class TestFormatDuration:
    def test_format_duration_if_empty(self):
        assert format_duration(None) == ""
        assert format_duration(0) == ""

    def test_format_duration_if_less_than_one_minute(self):
        assert format_duration(30) == "<1min"

    def test_format_duration_if_less_than_ten_minutes(self):
        assert format_duration(540) == "9min"

    def test_format_duration_if_less_than_one_hour(self):
        assert format_duration(2400) == "40min"

    def test_format_duration_if_more_than_one_hour(self):
        assert format_duration(9000) == "2h 30min"


class TestDurationInSeconds:
    def test_duration_in_seconds_if_empty(self):
        assert duration_in_seconds(None) == 0
        assert duration_in_seconds("") == 0

    def test_duration_in_seconds_invalid_string(self):
        assert duration_in_seconds("oops") == 0

    def test_duration_in_seconds_hours_minutes_seconds(self):
        assert duration_in_seconds("2:30:40") == 9040

    def test_duration_in_seconds_hours_minutes_seconds_extra_digit(self):
        assert duration_in_seconds("2:30:40:2903903") == 9040

    def test_duration_in_seconds_minutes_seconds(self):
        assert duration_in_seconds("30:40") == 1840

    def test_duration_in_seconds_seconds_only(self):
        assert duration_in_seconds("40") == 40
