import http

from django.test import TestCase

from audiotrails.episodes.factories import EpisodeFactory


class EpisodeSitemapTests(TestCase):
    def test_get(self) -> None:
        EpisodeFactory.create_batch(12)
        resp = self.client.get("/sitemap-episodes.xml")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp["Content-Type"], "application/xml")
