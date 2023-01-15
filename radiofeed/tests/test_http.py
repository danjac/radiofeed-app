from __future__ import annotations

import datetime

import httpx
import pytest

from radiofeed.http import (
    build_absolute_uri,
    urlsafe_decode,
    urlsafe_encode,
    user_agent,
)


class TestBuildAbsoluteUri:
    BASE_URL = "http://example.com"

    SEARCH_URL = "/podcasts/search/"
    DETAIL_URL = "/podcasts/12345/test/"

    def test_no_url(self, db):
        assert build_absolute_uri() == self.BASE_URL + "/"

    def test_with_url(self, db):
        assert build_absolute_uri("/podcasts/") == self.BASE_URL + "/podcasts/"

    def test_with_request(self, rf):
        assert build_absolute_uri(request=rf.get("/")) == "http://testserver/"

    def test_https(self, db, settings):
        settings.HTTP_PROTOCOL = "https"
        assert build_absolute_uri() == "https://example.com/"


class TestUrlsafeEncode:
    def test_encode(self):
        assert urlsafe_encode("testing")


class TestUrlsafeDecode:
    def test_ok(self):
        assert urlsafe_decode(urlsafe_encode("testing")) == "testing"

    def test_bad_signing(self):
        with pytest.raises(ValueError):
            urlsafe_decode(
                "bHR0cHM6Ly9tZWdhcGhvbmUuaW1naXgubmV0L3BvZGNhc3RzL2IwOTEwZTMwLTMyNzgtMTFlYy05ZDUyLTViOGU5MzQ1MmFjYS9pbWFnZS9CVU5LRVJfVElMRVNfY29weV8yLnBuZz9peGxpYj1yYWlscy0yLjEuMiZtYXgtdz0zMDAwJm1heC1oPTMwMDAmZml0PWNyb3AmYXV0bz1mb3JtYXQsY29tcHJlc3M6TnNGdVZBTDFheTZ1OGs0VEpfV2ZsdXVZUEZ2T3Vockd2WnNuQVpZMk53SQ"
            )

    def test_bad_encoding(self):
        with pytest.raises(ValueError):
            urlsafe_decode("testing")


class TestUserAgent:
    @pytest.fixture
    def mock_now(self, mocker):
        mocker.patch(
            "django.utils.timezone.now",
            return_value=datetime.datetime(year=2022, month=12, day=30),
        )

    def test_ok(self, db, mock_now):
        assert (
            user_agent()
            == f"python-httpx/{httpx.__version__} (Radiofeed/2022-30-12; +http://example.com/)"
        )
