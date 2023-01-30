from __future__ import annotations

import pytest

from radiofeed.markup import clean_html, markdown, strip_html


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


class TestCleanHtml:
    def test_if_none(self):
        assert clean_html(None) == ""

    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert clean_html(text) == text

    def test_has_link_link(self):
        clean_htmled = clean_html('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="nofollow"' in clean_htmled

    def test_unsafe(self):
        assert clean_html("<script>alert('xss ahoy!')</script>") == "<div></div>"


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
