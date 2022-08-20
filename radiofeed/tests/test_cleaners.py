from __future__ import annotations

import pytest

from radiofeed import cleaners


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
        return cleaners.strip_html(value) == expected
