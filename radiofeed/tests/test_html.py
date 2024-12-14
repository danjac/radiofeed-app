import pytest

from radiofeed.html import linkify, render_markdown, strip_extra_spaces, strip_html


class TestLinkify:
    def test_no_links(self):
        assert linkify("no links here") == "no links here"

    def test_already_in_link(self):
        assert (
            linkify('<a href="https://example.com">example</a>')
            == '<a href="https://example.com">example</a>'
        )

    def test_not_linked(self):
        assert (
            linkify("<p>https://example.com</p>")
            == '<p><a href="https://example.com" rel="nofollow">https://example.com</a></p>'
        )


class TestRenderMarkdown:
    def test_empty(self):
        assert render_markdown("") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert render_markdown(text) == text

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert render_markdown(text) == "<p>testing with paras</p>"

    def test_has_link(self):
        cleaned = render_markdown('<a href="https://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_is_unlinked(self):
        cleaned = str(
            render_markdown(
                '<div><a href="https://reddit.com">Reddit</a> https://example.com</div>'
            )
        )
        assert cleaned.count('href="https://example.com"') == 1
        assert cleaned.count('href="https://reddit.com"') == 1

    def test_unsafe(self):
        assert render_markdown("<script>alert('xss ahoy!')</script>") == ""


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
