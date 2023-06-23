import pytest
from django.http import HttpResponse
from django_htmx.middleware import HtmxDetails, HtmxMiddleware

from radiofeed.middleware import (
    CacheControlMiddleware,
    HtmxMessagesMiddleware,
    Ordering,
    OrderingMiddleware,
    Pagination,
    PaginationMiddleware,
    Search,
    SearchMiddleware,
)


@pytest.fixture()
def htmx_mw(get_response):
    return HtmxMiddleware(get_response)


@pytest.fixture()
def req(rf):
    return rf.get("/")


@pytest.fixture()
def htmx_req(rf):
    return rf.get("/", HTTP_HX_REQUEST="true")


class TestCacheControlMiddleware:
    @pytest.fixture()
    def cache_mw(self, get_response):
        return CacheControlMiddleware(get_response)

    def test_is_htmx_request_cache_control_already_set(self, rf):
        def _get_response(request):
            request.htmx = True
            resp = HttpResponse()
            resp["Cache-Control"] = "max-age=3600"
            return resp

        req = rf.get("/")
        req.htmx = True

        resp = CacheControlMiddleware(_get_response)(req)
        assert resp.headers["Cache-Control"] == "max-age=3600"

    def test_is_htmx_request(self, htmx_req, htmx_mw, cache_mw):
        htmx_mw(htmx_req)
        resp = cache_mw(htmx_req)
        assert resp.headers["Cache-Control"] == "no-store, max-age=0"

    def test_is_not_htmx_request(self, req, htmx_mw, cache_mw):
        htmx_mw(req)
        resp = cache_mw(req)
        assert "Cache-Control" not in resp.headers


class TestOrderingMiddleware:
    @pytest.fixture()
    def mw(self, get_response):
        return OrderingMiddleware(get_response)

    def test_ordering(self, rf, mw):
        req = rf.get("/")
        mw(req)
        assert req.ordering.value == "desc"


class TestSearchMiddleware:
    @pytest.fixture()
    def mw(self, get_response):
        return SearchMiddleware(get_response)

    def test_search(self, rf, mw):
        req = rf.get("/", {"query": "testing"})
        mw(req)
        assert req.search
        assert str(req.search) == "testing"

    def test_no_search(self, req, mw):
        mw(req)
        assert not req.search
        assert not str(req.search)


class TestHtmxMiddleware:
    @pytest.fixture()
    def mw(self, get_response):
        return HtmxMessagesMiddleware(get_response)

    @pytest.fixture()
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
        req = rf.get("/", HTTP_HX_REQUEST="true")
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
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        req._messages = messages
        resp = mw(req)
        assert b"OK" not in resp.content


class TestPaginationMiddleware:
    @pytest.fixture()
    def mw(self, get_response):
        return PaginationMiddleware(get_response)

    def test_page(self, req, mw):
        mw(req)
        assert req.pagination.url(1) == "/?page=1"


class TestPagination:
    def test_append_page_number_to_querystring(self, rf):
        req = rf.get("/search/", {"query": "test"})
        page = Pagination(req)

        url = page.url(5)
        assert url.startswith("/search/?")
        assert "query=test" in url
        assert "page=5" in url

    def test_current_page(self, rf):
        req = rf.get("/", {"page": "100"})
        page = Pagination(req)

        assert page.current == "100"
        assert str(page) == "100"

    def test_current_page_empty(self, rf):
        req = rf.get("/")
        page = Pagination(req)

        assert page.current == ""
        assert not str(page)


class TestSearch:
    def test_search(self, rf):
        req = rf.get("/", {"query": "testing"})
        search = Search(req)
        assert search
        assert str(search) == "testing"
        assert search.qs == "query=testing"

    def test_no_search(self, rf):
        req = rf.get("/")
        search = Search(req)
        assert not search
        assert not str(search)
        assert search.qs == ""


class TestOrdering:
    def test_default_value(self, rf):
        req = rf.get("/")
        ordering = Ordering(req)
        assert ordering.value == "desc"
        assert ordering.is_desc

    def test_asc_value(self, rf):
        req = rf.get("/", {"order": "asc"})
        ordering = Ordering(req)
        assert ordering.value == "asc"
        assert ordering.is_asc

    def test_desc_value(self, rf):
        req = rf.get("/", {"order": "desc"})
        ordering = Ordering(req)
        assert ordering.value == "desc"
        assert ordering.is_desc

    def test_str(self, rf):
        req = rf.get("/")
        ordering = Ordering(req)
        assert str(ordering) == "desc"

    def test_qs_reversed_if_asc(self, rf):
        req = rf.get("/", {"order": "asc"})
        ordering = Ordering(req)
        assert ordering.qs_reversed == "order=desc"

    def test_qs_reversed_if_desc(self, rf):
        req = rf.get("/", {"order": "desc"})
        ordering = Ordering(req)
        assert ordering.qs_reversed == "order=asc"
