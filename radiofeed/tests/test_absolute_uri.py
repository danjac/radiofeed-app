from __future__ import annotations

from radiofeed.absolute_uri import build_absolute_uri


class TestBuildAbsoluteUri:
    BASE_URL = "http://example.com"

    SEARCH_URL = "/podcasts/search/"
    DETAIL_URL = "/podcasts/12345/test/"

    def test_no_url(self, db):
        assert build_absolute_uri() == self.BASE_URL + "/"

    def test_with_url(self, db):
        assert build_absolute_uri("/podcasts/") == self.BASE_URL + "/podcasts/"

    def test_with_request(self, rf):
        assert build_absolute_uri(request=rf.get("/")) == "http://testserver/"

    def test_https(self, db, settings):
        settings.HTTP_PROTOCOL = "https"
        assert build_absolute_uri() == "https://example.com/"
