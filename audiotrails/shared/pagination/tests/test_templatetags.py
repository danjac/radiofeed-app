from django.test import RequestFactory, SimpleTestCase

from ..templatetags import pagination_url


class PaginationUrlTests(SimpleTestCase):
    def test_append_page_number_to_querystring(self):

        req = RequestFactory().get("/search/", {"q": "test"})
        url = pagination_url({"request": req}, 5)
        assert url.startswith("/search/?")
        assert "q=test" in url
        assert "page=5" in url
