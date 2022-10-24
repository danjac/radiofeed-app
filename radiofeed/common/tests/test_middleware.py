from __future__ import annotations

import pytest

from django_htmx.middleware import HtmxMiddleware

from radiofeed.common.middleware import (
    cache_control_middleware,
    search_middleware,
    sorter_middleware,
)


@pytest.fixture
def htmx_mw(get_response):
    return HtmxMiddleware(get_response)


@pytest.fixture
def req(rf):
    return rf.get("/")


@pytest.fixture
def htmx_req(rf):
    return rf.get("/", HTTP_HX_REQUEST="true")


class TestCacheControlMiddleware:
    @pytest.fixture
    def cache_mw(self, get_response):
        return cache_control_middleware(get_response)

    def test_is_htmx_request(self, htmx_req, htmx_mw, cache_mw):
        htmx_mw(htmx_req)
        resp = cache_mw(htmx_req)
        assert "Cache-Control" in resp.headers

    def test_is_not_htmx_request(self, req, htmx_mw, cache_mw):
        htmx_mw(req)
        resp = cache_mw(req)
        assert "Cache-Control" not in resp.headers


class TestSorterMiddleware:
    @pytest.fixture
    def mw(self, get_response):
        return sorter_middleware(get_response)

    def test_sorter(self, rf, mw):
        req = rf.get("/")
        mw(req)
        assert req.sorter.value == "desc"


class TestSearchMiddleware:
    @pytest.fixture
    def mw(self, get_response):
        return search_middleware(get_response)

    def test_search(self, rf, mw):
        req = rf.get("/", {"query": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self, req, mw):
        mw(req)
        assert not req.search
        assert not str(req.search)
