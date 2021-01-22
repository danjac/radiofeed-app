# Local
from . import SearchMiddleware


class TestSearchMiddleware:
    def test_search(self, rf, get_response):
        mw = SearchMiddleware(get_response)
        req = rf.get("/", {"q": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self, rf, get_response):
        mw = SearchMiddleware(get_response)
        req = rf.get("/")
        mw(req)
        assert not req.search
        assert str(req.search) == ""
