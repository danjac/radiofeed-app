import datetime

from zoneinfo import ZoneInfo

import pytz

from jcasts.podcasts.date_parser import parse_date, parse_timestamp

UTC = ZoneInfo(key="UTC")


class TestParseTimestamp:
    def test_parse_timestamp_if_none(self):
        assert parse_timestamp(None) is None

    def test_parse_timestamp(self):
        dt = parse_timestamp(1631905234)
        assert dt.tzinfo == UTC


class TestParseDate:
    def test_parse_date_if_empty_str(self):
        assert parse_date("") is None

    def test_parse_date_if_none(self):
        assert parse_date(None) is None

    def test_invalid_offset(self):
        assert parse_date("Sun, 14 Jan 2018 21:38:44 -4400") == datetime.datetime(
            2018, 1, 14, 21, 38, 44, tzinfo=pytz.UTC
        )

    def test_parse_date_if_not_tz_aware(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3)
        new_dt = parse_date(dt)

        assert new_dt.tzinfo == UTC

    def test_parse_date_if_date(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        assert parse_date(dt) == dt

    def test_parse_date_if_valid(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03 +0000") == dt

    def test_parse_date_if_no_tz(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03") == dt

    def test_parse_date_if_invalid(self):
        assert parse_date("Fri, 33 June 2020 16:58:03 +0000") is None
