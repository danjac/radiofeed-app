from __future__ import annotations

from radiofeed.common.search import Search


class TestSearch:
    def test_search(self, rf):
        req = rf.get("/", {"q": "testing"})
        search = Search(req)
        assert search
        assert str(search) == "testing"
        assert search.qs == "q=testing"

    def test_no_search(self, rf):
        req = rf.get("/")
        search = Search(req)
        assert not search
        assert str(search) == ""
        assert search.qs == ""
