import json

import pytest

from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.http import HttpResponse, HttpResponseRedirect
from django_htmx.middleware import HtmxMiddleware

from jcasts.lib.middleware import (
    CacheControlMiddleware,
    HtmxMessageMiddleware,
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
    return rf.get("/", HTTP_HX_REQUEST="true")


class TestCacheControlMiddleware:
    @pytest.fixture
    def cache_mw(self, get_response):
        return CacheControlMiddleware(get_response)

    def test_is_htmx_request(self, htmx_req, htmx_mw, cache_mw):
        htmx_mw(htmx_req)
        resp = cache_mw(htmx_req)
        assert "Cache-Control" in resp.headers

    def test_is_not_htmx_request(self, req, htmx_mw, cache_mw):
        htmx_mw(req)
        resp = cache_mw(req)
        assert "Cache-Control" not in resp.headers


class TestSearchMiddleware:
    @pytest.fixture
    def mw(self, get_response):
        return SearchMiddleware(get_response)

    def test_search(self, rf, mw):
        req = rf.get("/", {"q": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self, req, mw):
        mw(req)
        assert not req.search
        assert str(req.search) == ""


class TestHtmxMessageMiddleware:
    message = "It works!"
    message_level = "message-success"

    @pytest.fixture
    def message_mw(self, get_response):
        return HtmxMessageMiddleware(get_response)

    @pytest.fixture
    def messages(self, mocker):
        mocker.patch(
            "jcasts.lib.middleware.get_messages",
            return_value=[Message(messages.SUCCESS, self.message)],
        )

    @pytest.fixture
    def no_messages(self, mocker):
        mocker.patch("jcasts.lib.middleware.get_messages", return_value=[])

    def _test_not_htmx(self, req, htmx_mw, message_mw):
        htmx_mw(req)
        resp = message_mw(req)
        assert "HX-Trigger" not in resp.headers

    def test_not_htmx_no_messages(self, req, htmx_mw, message_mw, no_messages):
        self._test_not_htmx(req, htmx_mw, message_mw)

    def test_not_htmx_messages(self, req, mocker, htmx_mw, message_mw, messages):
        self._test_not_htmx(req, htmx_mw, message_mw)

    def test_htmx_no_messages(self, htmx_req, htmx_mw, message_mw, no_messages):
        htmx_mw(htmx_req)
        resp = message_mw(htmx_req)
        assert "HX-Trigger" not in resp.headers

    def test_htmx_messages(self, htmx_req, htmx_mw, message_mw, messages):
        htmx_mw(htmx_req)
        resp = message_mw(htmx_req)
        assert "HX-Trigger" in resp.headers
        data = json.loads(resp.headers["HX-Trigger"])
        assert data == {
            "messages": [
                {
                    "message": self.message,
                    "tags": self.message_level,
                },
            ],
        }

    def test_htmx_messages_redirect(self, htmx_req, htmx_mw, message_mw, messages):
        def _get_response(request):
            return HttpResponseRedirect("/")

        htmx_mw(htmx_req)
        resp = HtmxMessageMiddleware(_get_response)(htmx_req)
        assert "HX-Trigger" not in resp

    def test_htmx_messages_existing_hx_header(self, htmx_req, htmx_mw, messages):
        def _get_response(request):
            resp = HttpResponse()
            resp["HX-Trigger"] = "reload-queue"
            return resp

        htmx_mw(htmx_req)
        resp = HtmxMessageMiddleware(_get_response)(htmx_req)
        data = json.loads(resp.headers["HX-Trigger"])
        assert data == {
            "reload-queue": "",
            "messages": [
                {
                    "message": self.message,
                    "tags": self.message_level,
                },
            ],
        }

    def test_htmx_messages_existing_hx_multiple_header(
        self, htmx_req, htmx_mw, messages
    ):
        def _get_response(request):
            resp = HttpResponse()
            resp["HX-Trigger"] = json.dumps({"reload-queue": "", "start-player": ""})
            return resp

        htmx_mw(htmx_req)
        resp = HtmxMessageMiddleware(_get_response)(htmx_req)
        data = json.loads(resp.headers["HX-Trigger"])
        assert data == {
            "reload-queue": "",
            "start-player": "",
            "messages": [
                {
                    "message": self.message,
                    "tags": self.message_level,
                },
            ],
        }
