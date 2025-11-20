from radiofeed.markdown import markdownify


class TestMarkdownify:
    def test_empty(self):
        assert markdownify("") == ""

    def test_whitespace(self):
        assert markdownify("  \t\n") == ""

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

    def test_unsafe(self):
        assert markdownify("<script>alert('xss ahoy!')</script>") == ""
