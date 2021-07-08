from audiotrails.episodes.factories import EpisodeFactory
from audiotrails.shared.assertions import assert_ok


class TestEpisodeSitemap:
    def test_get(self, client, db):
        EpisodeFactory.create_batch(12)
        resp = client.get("/sitemap-episodes.xml")
        assert_ok(resp)
        assert resp["Content-Type"] == "application/xml"
