from radiofeed.markdown import markdownify


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
