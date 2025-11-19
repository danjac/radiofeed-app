import pytest
from bs4.element import NavigableString

from radiofeed import html


class TestLinkify:
    def test_no_links(self):
        assert html.linkify("no links here") == "no links here"

    def test_already_in_link(self):
        assert (
            html.linkify('<a href="https://example.com">example</a>')
            == '<a href="https://example.com">example</a>'
        )

    def test_not_linked(self):
        assert (
            html.linkify("<p>https://example.com</p>")
            == '<p><a href="https://example.com" rel="nofollow">https://example.com</a></p>'
        )

    def test_trailing_punctuation(self):
        result = html.linkify("<p>https://example.com?!</p>")
        assert (
            '<a href="https://example.com" rel="nofollow">https://example.com</a>?!'
            in result
        )

    def test_www_normalized(self):
        result = html.linkify("<p>www.example.com</p>")
        assert 'href="https://www.example.com"' in result


class TestLinkifyNode:
    def test_linkify_node_no_replacements(self):
        soup = html.make_soup("plain text")
        node = soup.string
        assert isinstance(node, NavigableString)
        html.linkify_node(soup, node)
        assert str(soup) == "plain text"

    def test_linkify_node_with_replacements(self):
        soup = html.make_soup("visit https://example.com now")
        node = soup.string
        assert isinstance(node, NavigableString)
        html.linkify_node(soup, node)
        assert '<a href="https://example.com"' in str(soup)


class TestInsertLinks:
    def test_insert_links(self):
        soup = html.make_soup("")
        replacements = list(html.insert_links(soup, "https://example.com end"))
        assert len(replacements) == 2
        anchor = replacements[0]
        assert getattr(anchor, "name", None) == "a"


class TestFindUrlMatches:
    def test_find_url_matches_skip_overlap_and_empty(self, monkeypatch):
        class FakeMatch:
            def __init__(self, span, url):
                self._span = span
                self._url = url

            def span(self):
                return self._span

            def group(self, name):
                assert name == "url"
                return self._url

        class FakePattern:
            def __init__(self, matches):
                self._matches = matches

            def finditer(self, _):
                return iter(self._matches)

        fake_matches = [
            FakeMatch((0, 5), "https://example.com"),
            FakeMatch((2, 4), "...)"),  # overlapping, should be skipped
            FakeMatch((6, 8), "...)"),  # becomes empty after stripping
        ]
        monkeypatch.setattr(
            html, "_LINKIFY_PATTERN", FakePattern(fake_matches), raising=False
        )
        match = html.UrlMatch(start=0, end=5, url="https://example.com", trailing="")
        assert list(html.find_url_matches("ignored")) == [match]


class TestRenderMarkdown:
    def test_empty(self):
        assert html.render_markdown("") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert html.render_markdown(text) == text

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert html.render_markdown(text) == "<p>testing with paras</p>"

    def test_has_link(self):
        cleaned = html.render_markdown('<a href="https://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_is_unlinked(self):
        cleaned = str(
            html.render_markdown(
                '<div><a href="https://reddit.com">Reddit</a> https://example.com</div>'
            )
        )
        assert cleaned.count('href="https://example.com"') == 1
        assert cleaned.count('href="https://reddit.com"') == 1

    def test_unsafe(self):
        assert html.render_markdown("<script>alert('xss ahoy!')</script>") == ""


class TestCleanHtml:
    def test_clean_html(self):
        result = html._clean_html("<script>bad()</script><p>ok</p>")
        assert result == "<p>ok</p>"


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
        assert html.strip_html(value) == expected


class TestStripExtraSpaces:
    def test_strip_extra_spaces(self):
        value = """
        This is some text
        with  a line    break


        and some extra line breaks!


        """

        expected = "This is some text\nwith a line break\nand some extra line breaks!"

        assert html.strip_extra_spaces(value) == expected
