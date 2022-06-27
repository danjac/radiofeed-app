from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory


class TestCategorySitemap:
    def test_get(self, client, db, assert_ok):
        CategoryFactory.create_batch(12)
        resp = client.get("/sitemap-categories.xml")
        assert_ok(resp)
        assert resp["Content-Type"] == "application/xml"


class TestPodcastSitemap:
    def test_get(self, client, db, assert_ok):
        PodcastFactory.create_batch(12)
        resp = client.get("/sitemap-podcasts.xml")
        assert_ok(resp)
        assert resp["Content-Type"] == "application/xml"
