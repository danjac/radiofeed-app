from radiofeed.markdown import render


class TestRender:
    def test_empty(self):
        assert render("") == ""

    def test_include_allowed_tag(self):
        text = "<p>testing with paras</p>"
        assert render(text) == text

    def test_remove_attrs(self):
        text = "<p onload='alert(\"hi\")'>testing with paras</p>"
        assert render(text) == "<p>testing with paras</p>"

    def test_has_link(self):
        cleaned = render('<a href="http://reddit.com">Reddit</a>')
        assert 'rel="noopener noreferrer nofollow"' in cleaned
        assert 'target="_blank"' in cleaned

    def test_unsafe(self):
        assert render("<script>alert('xss ahoy!')</script>") == ""
