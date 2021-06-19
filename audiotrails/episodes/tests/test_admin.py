from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from audiotrails.episodes.admin import EpisodeAdmin
from audiotrails.episodes.factories import EpisodeFactory
from audiotrails.episodes.models import Episode


class EpisodeAdminTests(TestCase):
    def setUp(self) -> None:
        self.rf = RequestFactory()
        self.admin = EpisodeAdmin(Episode, AdminSite())
        self.request = self.rf.get("/")

    def test_episode_title(self) -> None:
        episode = EpisodeFactory(title="testing")
        self.assertEqual(self.admin.episode_title(episode), "testing")

    def test_podcast_title(self) -> None:
        episode = EpisodeFactory(podcast__title="testing")
        self.assertEqual(self.admin.podcast_title(episode), "testing")

    def test_get_search_results_no_search_term(self) -> None:
        EpisodeFactory.create_batch(3)
        qs, _ = self.admin.get_search_results(self.request, Episode.objects.all(), "")
        self.assertEqual(qs.count(), 3)

    def test_get_search_results(self) -> None:
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory(title="testing python")

        qs, _ = self.admin.get_search_results(
            self.request, Episode.objects.all(), "testing python"
        )
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), episode)
