from __future__ import annotations

import pytest

from radiofeed import markup


class TestClean:
    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert markup.clean(text) == text

    def test_has_link_link(self):
        text = '<a href="http://reddit.com">Reddit</a>'
        clean = markup.clean(text)
        assert 'target="_blank"' in clean
        assert 'rel="noopener noreferrer nofollow"' in clean

    def test_unsafe(self):
        text = "<script>alert('xss ahoy!')</script>"
        assert markup.clean(text) == "alert('xss ahoy!')"


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
        return markup.strip_html(value) == expected


class TestMarkdown:
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
        return markup.markdown(value) == expected
