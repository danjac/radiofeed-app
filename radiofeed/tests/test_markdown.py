from radiofeed.markdown import render_markdown


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
        cleaned = render_markdown('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_unsafe(self):
        assert render_markdown("<script>alert('xss ahoy!')</script>") == ""
