import pytest

from simplecasts.sanitizer import markdown, strip_extra_spaces, strip_html


class TestMarkdown:
    def test_empty(self):
        assert markdown("") == ""

    def test_whitespace(self):
        assert markdown("  \t\n") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert markdown(text) == text + "\n"

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert markdown(text) == "<p>testing with paras</p>\n"

    def test_has_link(self):
        cleaned = markdown('<a href="https://reddit.com">Reddit</a>')
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


class TestStripExtraSpaces:
    def test_strip_extra_spaces(self):
        value = """
        This is some text
        with  a line    break


        and some extra line breaks!


        """
        expected = "This is some text\nwith a line break\nand some extra line breaks!"
        assert strip_extra_spaces(value) == expected
