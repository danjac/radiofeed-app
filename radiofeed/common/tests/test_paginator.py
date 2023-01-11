from __future__ import annotations

from radiofeed.common.paginator import Paginator


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):

        req = rf.get("/search/", {"query": "test"})
        paginator = Paginator(req)

        url = paginator.url(req, 5)
        assert url.startswith("/search/?")
        assert "query=test" in url
        assert "page=5" in url
