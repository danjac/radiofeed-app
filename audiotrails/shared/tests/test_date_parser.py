import datetime

import pytz

from django.test import SimpleTestCase

from audiotrails.shared.date_parser import parse_date


class ParseDateTests(SimpleTestCase):
    def test_parse_date_if_valid(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03 +0000"), dt)

    def test_parse_date_if_no_tz(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03"), dt)

    def test_parse_date_if_invalid(self) -> None:
        self.assertEqual(parse_date("Fri, 33 June 2020 16:58:03 +0000"), None)
