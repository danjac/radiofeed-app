from __future__ import annotations

import pytest

from radiofeed.common import html


class TestClean:
    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert html.clean(text) == text

    def test_has_link_link(self):
        text = '<a href="http://reddit.com">Reddit</a>'
        clean = html.clean(text)
        assert 'target="_blank"' in clean
        assert 'rel="noopener noreferrer nofollow"' in clean

    def test_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        assert html.clean(text) == "alert('xss ahoy!')"


class TestStripHtml:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("", ""),
            ("<p>this &amp; that</p>", "this & that"),
        ],
    )
    def test_strip_html(self, value, expected):
        return html.strip_html(value) == expected


class TestMarkup:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            (" ", ""),
            ("*test*", "<b>test</b>"),
            ("<p>test</p>", "<p>test</p>"),
            ("<script>alert('xss ahoy!')</script>", "alert('xss ahoy!')"),
        ],
    )
    def test_markup(self, value, expected):
        return html.markup(value) == expected
