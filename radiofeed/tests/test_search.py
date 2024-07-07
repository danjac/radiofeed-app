from radiofeed.middleware import SearchDetails


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
