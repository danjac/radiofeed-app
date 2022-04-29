from podtracker.common import cleaners


class TestClean:
    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert cleaners.clean(text) == text

    def test_has_link_link(self):
        text = '<a href="http://reddit.com">Reddit</a>'
        clean = cleaners.clean(text)
        assert 'target="_blank"' in clean
        assert 'rel="noopener noreferrer nofollow"' in clean

    def test_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        assert cleaners.clean(text) == "alert('xss ahoy!')"


class TestStripHtml:
    def test_value_none(self):
        return cleaners.strip_html(None) == ""

    def test_value_empty(self):
        return cleaners.strip_html("") == ""

    def test_value_has_content(self):
        return cleaners.strip_html("<p>this &amp; that</p>") == "this & that"


class TestMarkup:
    def test_value_none(self):
        return cleaners.markup(None) == ""

    def test_value_empty(self):
        return cleaners.markup("  ") == ""

    def test_markdown(self):
        return cleaners.markup("*test*") == "<b>test</b>"

    def test_html(self):
        return cleaners.markup("<p>test</p>") == "<p>test</p>"

    def test_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        assert cleaners.markup(text) == "alert('xss ahoy!')"
