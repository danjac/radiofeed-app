from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, SimpleTestCase

from audiotrails.shared.middleware import SearchMiddleware


def get_response(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


class SearchMiddlewareTests(SimpleTestCase):
    def setUp(self) -> None:
        self.rf = RequestFactory()
        self.mw = SearchMiddleware(get_response)

    def test_search(self) -> None:
        req = self.rf.get("/", {"q": "testing"})
        self.mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self) -> None:
        req = self.rf.get("/")
        self.mw(req)
        assert not req.search
        assert str(req.search) == ""
