from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from . import SearchMiddleware


def get_response(request):
    return HttpResponse()


class SearchMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_search(self):
        mw = SearchMiddleware(get_response)
        req = self.rf.get("/", {"q": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self):
        mw = SearchMiddleware(get_response)
        req = self.rf.get("/")
        mw(req)
        assert not req.search
        assert str(req.search) == ""
