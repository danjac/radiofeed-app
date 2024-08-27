import pytest

from radiofeed.search.middleware import (
    SearchDetails,
    SearchMiddleware,
)


@pytest.fixture
def req(rf):
    return rf.get("/")


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
        search = SearchDetails(req)
        assert search
        assert str(search) == "testing"
        assert search.qs == "?search=testing"

    def test_no_search(self, rf):
        req = rf.get("/")
        search = SearchDetails(req)
        assert not search
        assert not str(search)
        assert search.qs == ""
