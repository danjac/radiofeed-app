import datetime

import pytz

from django.test import SimpleTestCase

from audiotrails.common.utils.date_parser import parse_date
from audiotrails.common.utils.html import clean_html_content, stripentities


class TestCleanHtmlContent(SimpleTestCase):
    def test_clean_html_content_if_safe(self) -> None:
        text = "<p>testing with paras</p>"
        self.assertEqual(clean_html_content(text), text)

    def test_clean_html_content_if_unsafe(self) -> None:
        text = "<script>alert('xss ahoy!')</script>"
        self.assertEqual(clean_html_content(text), "alert('xss ahoy!')")

    def test_named_stripentities(self) -> None:
        text = "this &amp; that"
        self.assertEqual(stripentities(text), "this & that")

    def test_numeric_stripentities(self) -> None:
        text = "gov&#8217;t"
        self.assertEqual(stripentities(text), "gov’t")


class ParseDateTests(SimpleTestCase):
    def test_parse_date_if_valid(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03 +0000"), dt)

    def test_parse_date_if_no_tz(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03"), dt)

    def test_parse_date_if_invalid(self) -> None:
        self.assertEqual(parse_date("Fri, 33 June 2020 16:58:03 +0000"), None)
