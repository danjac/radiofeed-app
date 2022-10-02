from __future__ import annotations

from radiofeed.common.search import Search
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast


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
        assert not str(search)
        assert search.qs == ""

    def test_filter_queryset(self, rf, db):
        podcast = PodcastFactory(title="testing")
        req = rf.get("/", {"q": "testing"})
        search = Search(req)
        assert search.filter_queryset(Podcast.objects.all()).first() == podcast
