from __future__ import annotations

import pytest

from radiofeed.common import markup


class TestMarkup:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("   ", ""),
            ("test", "test"),
            ("*test*", "<b>test</b>"),
            ("<p>test</p>", "<p>test</p>"),
            ("<p>test</p>   ", "<p>test</p>"),
            ("<script>test</script>", "test"),
        ],
    )
    def test_markup(self, value, expected):
        return markup.markup(value) == expected


class TestClean:
    def test_if_none(self):
        assert markup.clean(None) == ""

    def test_if_safe(self):
        text = "<p>testing with paras</p>"
        assert markup.clean(text) == text

    def test_has_link_link(self):
        cleaned = markup.clean('<a href="http://reddit.com">Reddit</a>')
        assert 'target="_blank"' in cleaned
        assert 'rel="noopener noreferrer nofollow"' in cleaned

    def test_unsafe(self):
        assert (
            markup.clean("<script>alert('xss ahoy!')</script>") == "alert('xss ahoy!')"
        )


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
