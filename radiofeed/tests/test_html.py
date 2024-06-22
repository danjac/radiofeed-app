import pytest

from radiofeed.html import strip_html


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
