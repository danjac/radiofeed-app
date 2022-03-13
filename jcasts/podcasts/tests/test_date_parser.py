import datetime

from zoneinfo import ZoneInfo

from jcasts.podcasts.parsers.date_parser import parse_date

UTC = ZoneInfo(key="UTC")


class TestParseDate:
    def test_parse_date_if_empty_str(self):
        assert parse_date("") is None

    def test_parse_date_if_none(self):
        assert parse_date(None) is None

    def test_invalid_offset(self):
        assert parse_date("Sun, 14 Jan 2018 21:38:44 -4400") == datetime.datetime(
            2018, 1, 14, 21, 38, 44, tzinfo=UTC
        )

    def test_parse_date_if_not_tz_aware(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3)
        new_dt = parse_date(dt)

        assert new_dt.tzinfo == UTC

    def test_parse_date_if_datetime(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=UTC)
        assert parse_date(dt) == dt

    def test_parse_date_if_date(self):
        dt = datetime.date(2020, 6, 19)
        assert parse_date(dt) == datetime.datetime(2020, 6, 19, 0, 0, 0, tzinfo=UTC)

    def test_parse_date_if_valid(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03 +0000") == dt

    def test_parse_date_if_no_tz(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03") == dt

    def test_parse_date_if_invalid(self):
        assert parse_date("Fri, 33 June 2020 16:58:03 +0000") is None
