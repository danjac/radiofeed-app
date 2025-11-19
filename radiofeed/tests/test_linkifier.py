from radiofeed.linkifier import insert_links, linkify, make_soup


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
