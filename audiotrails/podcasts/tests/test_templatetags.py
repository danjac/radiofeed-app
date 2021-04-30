from django.test import TestCase

from ..factories import PodcastFactory
from ..models import _cover_image_placeholder
from ..templatetags.podcasts import cover_image


class CoverImageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.podcast = PodcastFactory()

    def test_lazy_cover_image_provided(self):
        dct = cover_image(self.podcast, cover_image=_cover_image_placeholder, lazy=True)
        self.assertTrue(dct["cover_image"])
        self.assertFalse(dct["lazy"])
        self.assertEqual(dct["podcast"], self.podcast)

    def test_lazy_cover_image_not_provided(self):
        dct = cover_image(self.podcast, cover_image=None, lazy=True)
        self.assertFalse(dct["cover_image"])
        self.assertTrue(dct["lazy"])
        self.assertEqual(dct["podcast"], self.podcast)

    def test_not_lazy(self):
        dct = cover_image(self.podcast, cover_image=None, lazy=False)
        self.assertTrue(dct["cover_image"])
        self.assertFalse(dct["lazy"])
        self.assertEqual(dct["podcast"], self.podcast)
