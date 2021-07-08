import pytest

from django.http import HttpRequest, HttpResponse
from django_htmx.middleware import HtmxMiddleware

from audiotrails.shared.middleware import CacheControlMiddleware, SearchMiddleware


def get_response(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


class TestCacheControlMiddleware:
    @pytest.fixture
    def htmx_mw(self):
        return HtmxMiddleware(get_response)

    @pytest.fixture
    def cache_mw(self):
        return CacheControlMiddleware(get_response)

    def test_is_htmx_request(self, rf, htmx_mw, cache_mw):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        htmx_mw(req)
        resp = cache_mw(req)
        assert "Cache-Control" in resp.headers

    def test_is_not_htmx_request(self, rf, htmx_mw, cache_mw):
        req = rf.get("/")
        htmx_mw(req)
        resp = cache_mw(req)
        assert "Cache-Control" not in resp.headers


class TestSearchMiddleware:
    @pytest.fixture
    def mw(self):
        return SearchMiddleware(get_response)

    def test_search(self, rf, mw):
        req = rf.get("/", {"q": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self, rf, mw):
        req = rf.get("/")
        mw(req)
        assert not req.search
        assert str(req.search) == ""
