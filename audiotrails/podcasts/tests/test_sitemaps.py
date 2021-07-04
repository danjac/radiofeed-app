import http

from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory


class TestCategorySitemap:
    def test_get(self, client, db):
        CategoryFactory.create_batch(12)
        resp = client.get("/sitemap-categories.xml")
        assert resp.status_code == http.HTTPStatus.OK
        assert resp["Content-Type"] == "application/xml"


class TestPodcastSitemap:
    def test_get(self, client, db):
        PodcastFactory.create_batch(12)
        resp = client.get("/sitemap-podcasts.xml")
        assert resp.status_code == http.HTTPStatus.OK
        assert resp["Content-Type"] == "application/xml"
