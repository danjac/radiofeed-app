import datetime
from zoneinfo import ZoneInfo

from radiofeed.feedparser.date_parser import parse_date

UTC = ZoneInfo(key="UTC")


class TestParseDate:
    def test_empty_str(self):
        assert parse_date("") is None

    def test_none(self):
        assert parse_date(None) is None

    def test_invalid_offset(self):
        assert parse_date("Sun, 14 Jan 2018 21:38:44 -4400") == datetime.datetime(
            2018, 1, 14, 21, 38, 44, tzinfo=UTC
        )

    def test_not_tz_aware(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3)
        new_dt = parse_date(dt)

        assert new_dt.tzinfo == UTC

    def test_datetime(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=UTC)
        assert parse_date(dt) == dt

    def test_date(self):
        dt = datetime.date(2020, 6, 19)
        assert parse_date(dt) == datetime.datetime(2020, 6, 19, 0, 0, 0, tzinfo=UTC)

    def test_valid_str(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03 +0000") == dt

    def test_no_tz_in_str(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03") == dt

    def test_invalid_str(self):
        assert parse_date("Fri, 33 June 2020 16:58:03 +0000") is None
