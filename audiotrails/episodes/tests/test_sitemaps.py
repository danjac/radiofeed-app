import http

from audiotrails.episodes.factories import EpisodeFactory


class TestEpisodeSitemap:
    def test_get(self, client, db):
        EpisodeFactory.create_batch(12)
        resp = client.get("/sitemap-episodes.xml")
        assert resp.status_code == http.HTTPStatus.OK
        assert resp["Content-Type"] == "application/xml"
