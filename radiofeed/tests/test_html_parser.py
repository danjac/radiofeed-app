from __future__ import annotations

import pytest

from radiofeed.html_parser import clean, markdown, strip_html


class TestMarkdown:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", ""),
            ("   ", ""),
            ("test", "test"),
            ("*test*", "<b>test</b>"),
            ("<p>test</p>", "<p>test</p>"),
            ("<p>test</p>   ", "<p>test</p>"),
            ("<script>test</script>", "test"),
        ],
    )
    def test_markdown(self, value, expected):
        return markdown(value) == expected


class TestClean:
    def test_if_none(self):
        assert clean(None) == ""

    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert clean(text) == text

    def test_has_link_link(self):
        cleaned = clean('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="nofollow"' in cleaned

    def test_unsafe(self):
        assert clean("<script>alert('xss ahoy!')</script>") == "<div></div>"


class TestStripHtml:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", ""),
            ("  ", ""),
            ("<p>this &amp; that</p>", "this & that"),
        ],
    )
    def test_strip_html(self, value, expected):
        return strip_html(value) == expected
