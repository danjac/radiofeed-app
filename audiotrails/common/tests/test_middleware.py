from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, SimpleTestCase

from audiotrails.common.middleware import (
    CacheControlMiddleware,
    HtmxMiddleware,
    SearchMiddleware,
)


def get_response(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


class HtmxMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.mw = HtmxMiddleware(get_response)

    def test_is_htmx_request(self) -> None:
        req = self.rf.get("/", HTTP_HX_REQUEST="true")
        self.mw(req)
        self.assertTrue(bool(req.htmx))

    def test_not_is_htmx_request(self) -> None:
        req = self.rf.get("/")
        self.mw(req)
        self.assertFalse(bool(req.htmx))

    def test_current_url(self) -> None:
        req = self.rf.get("/", HTTP_HX_CURRENT_URL="/test")
        self.mw(req)
        self.assertEqual(req.htmx.current_url, "/test")

    def test_prompt(self) -> None:
        req = self.rf.get("/", HTTP_HX_PROMPT="test")
        self.mw(req)
        self.assertEqual(req.htmx.prompt, "test")

    def test_target(self) -> None:
        req = self.rf.get("/", HTTP_HX_TARGET=".test")
        self.mw(req)
        self.assertEqual(req.htmx.target, ".test")

    def test_trigger(self) -> None:

        req = self.rf.get("/", HTTP_HX_TRIGGER="test")
        self.mw(req)
        self.assertEqual(req.htmx.trigger, "test")

    def test_trigger_name(self) -> None:

        req = self.rf.get("/", HTTP_HX_TRIGGER_NAME="test")
        self.mw(req)
        self.assertEqual(req.htmx.trigger_name, "test")


class CacheControlMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.htmx_mw = HtmxMiddleware(get_response)
        self.cache_mw = CacheControlMiddleware(get_response)

    def test_is_htmx_request(self) -> None:
        req = self.rf.get("/", HTTP_HX_REQUEST="true")
        self.htmx_mw(req)
        resp = self.cache_mw(req)
        self.assertTrue("Cache-Control" in resp.headers)

    def test_is_not_htmx_request(self) -> None:
        req = self.rf.get("/")
        self.htmx_mw(req)
        resp = self.cache_mw(req)
        self.assertFalse("Cache-Control" in resp.headers)


class SearchMiddlewareTests(SimpleTestCase):
    def setUp(self) -> None:
        self.rf = RequestFactory()
        self.mw = SearchMiddleware(get_response)

    def test_search(self) -> None:
        req = self.rf.get("/", {"q": "testing"})
        self.mw(req)
        self.assertTrue(req.search)
        self.assertEqual(str(req.search), "testing")

    def test_no_search(self) -> None:
        req = self.rf.get("/")
        self.mw(req)
        self.assertFalse(req.search)
        self.assertEqual(str(req.search), "")
