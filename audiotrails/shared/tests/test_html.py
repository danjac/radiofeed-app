from django.test import SimpleTestCase

from ..html import clean_html_content, stripentities


class TestCleanHtmlContent(SimpleTestCase):
    def test_clean_html_content_if_safe(self):
        text = "<p>testing with paras</p>"
        self.assertEqual(clean_html_content(text), text)

    def test_clean_html_content_if_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        self.assertEqual(clean_html_content(text), "alert('xss ahoy!')")

    def test_named_stripentities(self):
        text = "this &amp; that"
        self.assertEqual(stripentities(text), "this & that")

    def test_numeric_stripentities(self):
        text = "gov&#8217;t"
        self.assertEqual(stripentities(text), "gov’t")
