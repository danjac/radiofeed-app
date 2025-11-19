import pytest

from radiofeed.html_sanitizer import (
    insert_links,
    linkify,
    make_soup,
    markdownify,
    strip_extra_spaces,
    strip_html,
)


class TestMarkdownify:
    def test_empty(self):
        assert markdownify("") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert markdownify(text) == text

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert markdownify(text) == "<p>testing with paras</p>"

    def test_has_link(self):
        cleaned = markdownify('<a href="https://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_is_unlinked(self):
        cleaned = str(
            markdownify(
                '<div><a href="https://reddit.com">Reddit</a> https://example.com</div>'
            )
        )
        assert cleaned.count('href="https://example.com"') == 1
        assert cleaned.count('href="https://reddit.com"') == 1

    def test_unsafe(self):
        assert markdownify("<script>alert('xss ahoy!')</script>") == ""


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
            == '<p><a href="https://example.com" rel="noopener noreferrer nofollow">https://example.com</a></p>'
        )

    def test_trailing_punctuation(self):
        result = linkify("<p>https://example.com?!</p>")
        assert (
            '<a href="https://example.com" rel="noopener noreferrer nofollow">https://example.com</a>?!'
            in result
        )

    def test_www_normalized(self):
        result = linkify("<p>www.example.com</p>")
        assert 'href="https://www.example.com"' in result

    def test_no_replacement(self):
        result = linkify("plain text")
        assert result == "plain text"

    def test_insert_into_text(self):
        result = linkify("visit https://example.com now")
        assert '<a href="https://example.com"' in result


class TestInsertLinks:
    def test_insert_links(self):
        soup = make_soup("")
        replacements = list(insert_links(soup, "https://example.com end"))
        assert len(replacements) == 2
        anchor = replacements[0]
        assert getattr(anchor, "name", None) == "a"


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
