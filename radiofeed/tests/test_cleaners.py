from __future__ import annotations

import pytest

from radiofeed.cleaners import clean_html, strip_html


class TestCleanHtml:
    def test_empty(self):
        assert clean_html("") == ""

    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert clean_html(text) == text

    def test_has_link(self):
        cleaned = clean_html('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned

    def test_unsafe(self):
        assert clean_html("<script>alert('xss ahoy!')</script>") == ""


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
