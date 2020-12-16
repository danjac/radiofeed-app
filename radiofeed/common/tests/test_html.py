# Local
from ..html import clean_html_content, stripentities


class TestCleanHtmlContent:
    def test_clean_html_content_if_safe(self):
        text = "<p>testing with paras</p>"
        assert clean_html_content(text) == text

    def test_clean_html_content_if_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        assert clean_html_content(text) == "alert('xss ahoy!')"

    def test_named_stripentities(self):
        text = "this &amp; that"
        assert stripentities(text) == "this & that"

    def test_numeric_stripentities(self):
        text = "gov&#8217;t"
        assert stripentities(text) == "gov’t"
