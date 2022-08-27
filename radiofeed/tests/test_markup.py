from __future__ import annotations

import pytest

from radiofeed.markup import markdown


class TestMarkdown:
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
    def test_markdown(self, value, expected):
        return markdown(value) == expected
