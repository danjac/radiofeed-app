from podtracker.common.asserts import assert_ok
from podtracker.episodes.factories import EpisodeFactory


class TestEpisodeSitemap:
    def test_get(self, client, db):
        EpisodeFactory.create_batch(12)
        resp = client.get("/sitemap-episodes.xml")
        assert_ok(resp)
        assert resp["Content-Type"] == "application/xml"
