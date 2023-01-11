from __future__ import annotations

import datetime

import httpx
import pytest

from radiofeed.utils.http import build_absolute_uri, user_agent


class TestBuildAbsoluteUri:
    BASE_URL = "http://example.com"

    SEARCH_URL = "/podcasts/search/"
    DETAIL_URL = "/podcasts/12345/test/"

    def test_no_url(self, db):
        assert build_absolute_uri() == self.BASE_URL + "/"

    def test_request(self, rf):
        assert build_absolute_uri(request=rf.get("/")) == "http://testserver/"

    def test_https(self, db, settings):
        settings.SECURE_SSL_REDIRECT = True
        assert build_absolute_uri() == "https://example.com/"

    def test_with_url(self, db):
        url = build_absolute_uri(self.SEARCH_URL)
        assert url == self.BASE_URL + self.SEARCH_URL


class TestUserAgent:
    @pytest.fixture
    def mock_now(self, db, mocker):
        mocker.patch(
            "django.utils.timezone.now",
            return_value=datetime.datetime(year=2022, month=12, day=30),
        )

    def test_ok(self, db, mock_now):
        assert (
            user_agent()
            == f"python-httpx/{httpx.__version__} (Radiofeed/2022-30-12; +http://example.com/)"
        )
