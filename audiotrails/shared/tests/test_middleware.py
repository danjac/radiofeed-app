from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from ..middleware import SearchMiddleware


def get_response(request):
    return HttpResponse()


class SearchMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.mw = SearchMiddleware(get_response)

    def test_search(self):
        req = self.rf.get("/", {"q": "testing"})
        self.mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self):
        req = self.rf.get("/")
        self.mw(req)
        assert not req.search
        assert str(req.search) == ""
