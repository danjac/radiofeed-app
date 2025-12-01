from listenwave.markdown import markdown


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
