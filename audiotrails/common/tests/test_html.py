from django.test import SimpleTestCase

from audiotrails.common.html import clean_html_content, unescape


class CleanHtmlContentTests(SimpleTestCase):
    def test_clean_html_content_if_safe(self) -> None:
        text = "<p>testing with paras</p>"
        self.assertEqual(clean_html_content(text), text)

    def test_clean_html_content_if_link(self) -> None:
        text = '<a href="http://reddit.com">Reddit</a>'
        clean = clean_html_content(text)
        self.assertIn('target="_blank"', clean)
        self.assertIn('rel="noopener noreferrer nofollow"', clean)

    def test_clean_html_content_if_unsafe(self) -> None:
        text = "<script>alert('xss ahoy!')</script>"
        self.assertEqual(clean_html_content(text), "alert('xss ahoy!')")


class UnescapeTests(SimpleTestCase):
    def test_named_unescape(self) -> None:
        text = "this &amp; that"
        self.assertEqual(unescape(text), "this & that")

    def test_numeric_unescape(self) -> None:
        text = "gov&#8217;t"
        self.assertEqual(unescape(text), "gov’t")
