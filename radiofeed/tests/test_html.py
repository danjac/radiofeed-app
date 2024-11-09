import pytest

from radiofeed.html import render_markdown, strip_extra_spaces, strip_html, urlize


class TestRenderMarkdown:
    def test_empty(self):
        assert render_markdown("") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert render_markdown(text) == text

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert render_markdown(text) == "<p>testing with paras</p>"

    def test_has_link(self):
        cleaned = render_markdown('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_unsafe(self):
        assert render_markdown("<script>alert('xss ahoy!')</script>") == ""


class TestStripHtml:
    @pytest.mark.parametrize(
        (
            "value",
            "expected",
        ),
        [
            pytest.param("", "", id="empty"),
            pytest.param("  ", "", id="spaces"),
            pytest.param("<p>this &amp; that</p>", "this & that", id="html"),
        ],
    )
    def test_strip_html(self, value, expected):
        assert strip_html(value) == expected


class TestStripExtraSpaces:
    def test_strip_extra_spaces(self):
        value = """
        This is some text
        with  a line    break


        and some extra line breaks!


        """

        expected = "This is some text\nwith a line break\nand some extra line breaks!"

        assert strip_extra_spaces(value) == expected


class TestUrlize:
    def test_urlize(self):
        text = """I was surfing http://www.google.com, where I found my tweet,
check it out <a href="http://tinyurl.com/blah">http://tinyurl.com/blah</a>
<span>http://www.google.com</span>"""
        assert (
            urlize(text)
            == """I was surfing <a href="http://www.google.com">http://www.google.com</a>, where I found my tweet,
check it out <a href="http://tinyurl.com/blah">http://tinyurl.com/blah</a>
<span><a href="http://www.google.com">http://www.google.com</a></span>"""
        )
