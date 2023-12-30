import pytest

from radiofeed.feedparser import validators


class TestRequired:
    @pytest.mark.parametrize(
        ("value", "raises"),
        [
            pytest.param("ok", False, id="has value"),
            pytest.param("", True, id="empty"),
            pytest.param(None, True, id="none"),
        ],
    )
    def test_required(self, value, raises):
        if raises:
            with pytest.raises(ValueError, match="attr=None cannot be empty or None"):
                validators.required(None, None, value)
        else:
            validators.required(None, None, value)


class TestUrl:
    @pytest.mark.parametrize(
        ("value", "raises"),
        [
            pytest.param("http://example.com", False, id="valid HTTP URL"),
            pytest.param("https://example.com", False, id="valid HTTPS URL"),
            pytest.param("example", True, id="invalid URL"),
        ],
    )
    def test_url(self, value, raises):
        if raises:
            with pytest.raises(ValueError, match="attr=None must be a URL"):
                validators.url(None, None, value)
        else:
            validators.url(None, None, value)
