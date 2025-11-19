import json

import pytest
from django.http import HttpResponse
from django_htmx.middleware import HtmxDetails, HtmxMiddleware

from radiofeed.middleware import (
    HtmxCacheMiddleware,
    HtmxMessagesMiddleware,
    HtmxRedirectMiddleware,
    SearchDetails,
    SearchMiddleware,
)


@pytest.fixture
def htmx_mw(get_response):
    return HtmxMiddleware(get_response)


@pytest.fixture
def req(rf):
    return rf.get("/")


@pytest.fixture
def htmx_req(rf):
    return rf.get("/", headers={"Hx-Request": "true"})


class TestSearchMiddleware:
    @pytest.fixture
    def mw(self, get_response):
        return SearchMiddleware(get_response)

    def test_search(self, rf, mw):
        req = rf.get("/", {"search": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self, req, mw):
        mw(req)
        assert not req.search
        assert not str(req.search)


class TestSearchDetails:
    def test_search(self, rf):
        req = rf.get("/", {"search": "testing"})
        search = SearchDetails(request=req)
        assert search
        assert str(search) == "testing"
        assert search.qs == "?search=testing"

    def test_no_search(self, rf):
        req = rf.get("/")
        search = SearchDetails(request=req)
        assert not search
        assert not str(search)
        assert search.qs == ""


class TestHtmxRedirectMiddleware:
    @pytest.fixture
    def get_redirect_response(self):
        def _get_response(req):
            resp = HttpResponse()
            resp["Location"] = "/"
            return resp

        return _get_response

    def test_hx_redirect(self, rf, get_redirect_response):
        req = rf.get("/")
        req.htmx = True
        response = HtmxRedirectMiddleware(get_redirect_response)(req)
        assert response["HX-Location"] == json.dumps({"path": "/"})

    def test_not_htmx_redirect(self, rf, get_redirect_response):
        req = rf.get("/")
        req.htmx = False
        response = HtmxRedirectMiddleware(get_redirect_response)(req)
        assert "HX-Location" not in response
        assert response["Location"] == "/"


class TestHtmxCacheMiddleware:
    @pytest.fixture
    def cache_mw(self, get_response):
        return HtmxCacheMiddleware(get_response)

    def test_is_htmx_request(self, htmx_req, htmx_mw, cache_mw):
        htmx_mw(htmx_req)
        resp = cache_mw(htmx_req)
        assert resp.headers["Vary"] == "HX-Request"

    def test_is_not_htmx_request(self, req, htmx_mw, cache_mw):
        htmx_mw(req)
        resp = cache_mw(req)
        assert "Vary" not in resp.headers


class TestHtmxMessagesMiddleware:
    @pytest.fixture
    def mw(self, get_response):
        return HtmxMessagesMiddleware(get_response)

    @pytest.fixture
    def messages(self):
        return [
            {"message": "OK", "tags": "success"},
        ]

    def test_not_htmx(self, req, mw, messages):
        req.htmx = HtmxDetails(req)
        req._messages = messages
        resp = mw(req)
        assert b"OK" not in resp.content

    def test_htmx(self, rf, mw, messages):
        req = rf.get("/", headers={"Hx-Request": "true"})
        req.htmx = HtmxDetails(req)
        req._messages = messages
        resp = mw(req)
        assert b"OK" in resp.content

    def test_hx_redirect(self, rf, messages):
        def _get_response(req):
            resp = HttpResponse()
            resp["HX-Redirect"] = "/"
            return resp

        mw = HtmxMessagesMiddleware(_get_response)
        req = rf.get("/", headers={"Hx-Request": "true"})
        req.htmx = HtmxDetails(req)
        req._messages = messages
        resp = mw(req)
        assert b"OK" not in resp.content

    def test_streaming_response(self, rf, messages):
        def _get_response(_):
            resp = HttpResponse()
            resp.streaming = True
            return resp

        mw = HtmxMessagesMiddleware(_get_response)
        req = rf.get("/", headers={"Hx-Request": "true"})
        req.htmx = HtmxDetails(req)
        req._messages = messages
        resp = mw(req)
        assert b"OK" not in resp.content

    def test_non_html_response(self, rf, messages):
        def _get_response(_):
            return HttpResponse(content_type="application/json")

        mw = HtmxMessagesMiddleware(_get_response)
        req = rf.get("/", headers={"Hx-Request": "true"})
        req.htmx = HtmxDetails(req)
        req._messages = messages
        resp = mw(req)
        assert b"OK" not in resp.content
