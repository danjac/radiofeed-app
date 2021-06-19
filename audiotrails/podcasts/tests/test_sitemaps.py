import http

from django.test import TestCase

from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory


class CategorySitemapTests(TestCase):
    def test_get(self) -> None:
        CategoryFactory.create_batch(12)
        resp = self.client.get("/sitemap-categories.xml")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp["Content-Type"], "application/xml")


class PodcastSitemapTests(TestCase):
    def test_get(self) -> None:
        PodcastFactory.create_batch(12)
        resp = self.client.get("/sitemap-podcasts.xml")
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp["Content-Type"], "application/xml")
