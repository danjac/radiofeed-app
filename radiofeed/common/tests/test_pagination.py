from __future__ import annotations

from radiofeed.common.pagination import pagination_url


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):

        req = rf.get("/search/", {"q": "test"})
        url = pagination_url(req, 5)
        assert url.startswith("/search/?")
        assert "q=test" in url
        assert "p=5" in url
