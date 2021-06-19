import datetime

import pytz

from django.test import SimpleTestCase

from audiotrails.podcasts.date_parser import parse_date


class ParseDateTests(SimpleTestCase):
    def test_parse_date_if_empty_str(self) -> None:
        self.assertEqual(parse_date(""), None)

    def test_parse_date_if_none(self) -> None:
        self.assertEqual(parse_date(None), None)

    def test_parse_date_if_not_tz_aware(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3)
        new_dt = parse_date(dt)
        self.assertEqual(new_dt.tzinfo, pytz.UTC)

    def test_parse_date_if_date(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date(dt), dt)

    def test_parse_date_if_valid(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03 +0000"), dt)

    def test_parse_date_if_no_tz(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03"), dt)

    def test_parse_date_if_invalid(self) -> None:
        self.assertEqual(parse_date("Fri, 33 June 2020 16:58:03 +0000"), None)
