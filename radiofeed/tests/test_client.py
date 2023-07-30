import pytest
import requests

from radiofeed.client import HTTPClient


class TestHttpClient:
    def test_ok(self, mocker):
        class MockResponse:
            def raise_for_status(self):
                pass

        mocker.patch("requests.Session.get", return_value=MockResponse())
        assert HTTPClient().get("http://example.com")

    def test_error(self, mocker):
        class MockResponse:
            status_code = 404

            def raise_for_status(self):
                raise requests.HTTPError(response=self)

        mocker.patch("requests.Session.get", return_value=MockResponse())

        with pytest.raises(requests.HTTPError):
            assert HTTPClient().get("http://example.com")
