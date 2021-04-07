from django.http import HttpResponseRedirect

from . import RedirectException, RedirectExceptionMiddleware, SearchMiddleware


class TestRedirectExceptionMiddleware:
    def test_not_redirect_exception(self, rf, get_response):
        mw = RedirectExceptionMiddleware(get_response)
        assert mw.process_exception(rf.get("/"), ValueError("oops")) is None

    def test_redirect_exception(self, rf, get_response):
        mw = RedirectExceptionMiddleware(get_response)
        resp = HttpResponseRedirect("/")
        assert mw.process_exception(rf.get("/"), RedirectException(resp)) == resp


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
