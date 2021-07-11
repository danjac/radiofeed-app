import json

import pytest

from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest, HttpResponse
from django_htmx.middleware import HtmxMiddleware

from audiotrails.shared.middleware import (
    CacheControlMiddleware,
    HtmxMessageMiddleware,
    SearchMiddleware,
)


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


class TestHtmxMessageMiddleware:
    message = "It works!"
    message_level = "message-success"

    @pytest.fixture
    def htmx_mw(self):
        return HtmxMiddleware(get_response)

    @pytest.fixture
    def message_mw(self):
        return HtmxMessageMiddleware(get_response)

    @pytest.fixture
    def messages(self, mocker):
        mocker.patch(
            "audiotrails.shared.middleware.get_messages",
            return_value=[Message(messages.SUCCESS, self.message)],
        )

    @pytest.fixture
    def no_messages(self, mocker):
        mocker.patch("audiotrails.shared.middleware.get_messages", return_value=[])

    def _test_not_htmx(self, rf, htmx_mw, message_mw):
        req = rf.get("/")
        htmx_mw(req)
        resp = message_mw(req)
        assert "HX-Trigger" not in resp.headers

    def test_not_htmx_no_messages(self, rf, mocker, htmx_mw, message_mw, no_messages):
        self._test_not_htmx(rf, htmx_mw, message_mw)

    def test_not_htmx_messages(self, rf, mocker, htmx_mw, message_mw, messages):
        self._test_not_htmx(rf, htmx_mw, message_mw)

    def test_htmx_no_messages(self, rf, mocker, htmx_mw, message_mw, no_messages):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        htmx_mw(req)
        resp = message_mw(req)
        assert "HX-Trigger" not in resp.headers

    def test_htmx_messages(self, rf, mocker, htmx_mw, message_mw, messages):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        htmx_mw(req)
        resp = message_mw(req)
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

    def test_htmx_messages_existing_hx_header(self, rf, mocker, htmx_mw, messages):
        def _get_response(request):
            resp = HttpResponse()
            resp["HX-Trigger"] = "reload-queue"
            return resp

        req = rf.get("/", HTTP_HX_REQUEST="true")
        htmx_mw(req)
        resp = HtmxMessageMiddleware(_get_response)(req)
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
        self, rf, mocker, htmx_mw, messages
    ):
        def _get_response(request):
            resp = HttpResponse()
            resp["HX-Trigger"] = json.dumps({"reload-queue": "", "start-player": ""})
            return resp

        req = rf.get("/", HTTP_HX_REQUEST="true")
        htmx_mw(req)
        resp = HtmxMessageMiddleware(_get_response)(req)
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
