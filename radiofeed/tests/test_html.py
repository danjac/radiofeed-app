import pytest

from radiofeed.html import markdown, strip_html


class TestMarkdown:
    def test_empty(self):
        assert markdown("") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert markdown(text) == text

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert markdown(text) == "<p>testing with paras</p>"

    def test_has_link(self):
        cleaned = markdown('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_unsafe(self):
        assert markdown("<script>alert('xss ahoy!')</script>") == ""


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
