from jcasts.shared.html import clean_html_content, unescape


class TestCleanHtmlContent:
    def test_clean_html_content_if_safe(self):
        text = "<p>testing with paras</p>"
        assert clean_html_content(text) == text

    def test_clean_html_content_if_link(self):
        text = '<a href="http://reddit.com">Reddit</a>'
        clean = clean_html_content(text)
        assert 'target="_blank"' in clean
        assert 'rel="noopener noreferrer nofollow"' in clean

    def test_clean_html_content_if_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        assert clean_html_content(text) == "alert('xss ahoy!')"


class TestUnescape:
    def test_named_unescape(self):
        text = "this &amp; that"
        assert unescape(text) == "this & that"

    def test_numeric_unescape(self):
        text = "gov&#8217;t"
        assert unescape(text) == "gov’t"
