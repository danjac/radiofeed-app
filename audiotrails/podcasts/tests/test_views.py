import http

from typing import List, Tuple
from unittest.mock import Mock, patch

from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from audiotrails.episodes.factories import EpisodeFactory
from audiotrails.users.factories import UserFactory

from .. import itunes
from ..factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from ..itunes import SearchResult
from ..models import Follow, Podcast

mock_search_result = SearchResult(
    rss="http://example.com/test.xml",
    itunes="https://apple.com/some-link",
    image="test.jpg",
    title="test title",
)


def mock_fetch_itunes_genre(
    genre_id: int, num_results: int = 20
) -> Tuple[List[SearchResult], List[Podcast]]:
    return [mock_search_result], []


def mock_search_itunes(
    search_term: str, num_results: int = 12
) -> Tuple[List[SearchResult], List[Podcast]]:
    return [mock_search_result], []


class PreviewTests(TestCase):
    def test_preview(self) -> None:
        podcast = PodcastFactory()
        resp = self.client.get(reverse("podcasts:preview", args=[podcast.id]))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)


class AnonymousPodcastsTests(TestCase):
    def test_anonymous(self) -> None:
        PodcastFactory.create_batch(3, promoted=True)
        resp = self.client.get(reverse("podcasts:index"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)


class AuthenticatedPodcastsTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_user_is_following_featured(self) -> None:
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = FollowFactory(user=self.user).podcast
        resp = self.client.get(reverse("podcasts:featured"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)
        self.assertFalse(sub in resp.context_data["page_obj"].object_list)

    def test_user_is_not_following(self) -> None:
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        resp = self.client.get(reverse("podcasts:index"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)

    def test_user_is_following(self) -> None:
        """If user following any podcasts, show only own feed with these pdocasts"""

        PodcastFactory.create_batch(3)
        sub = FollowFactory(user=self.user)
        resp = self.client.get(reverse("podcasts:index"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], sub.podcast)


class SearchPodcastsTests(TestCase):
    def test_search_empty(self) -> None:
        self.assertRedirects(
            self.client.get(
                reverse("podcasts:search_podcasts"),
                {"q": ""},
            ),
            reverse("podcasts:index"),
        )

    def test_search(self) -> None:
        podcast = PodcastFactory(title="testing")
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        resp = self.client.get(
            reverse("podcasts:search_podcasts"),
            {"q": "testing"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)
        self.assertEqual(resp.context_data["page_obj"].object_list[0], podcast)


class PodcastRecommendationsTests(TestCase):
    def test_get(self) -> None:
        podcast = PodcastFactory()
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        resp = self.client.get(
            reverse("podcasts:podcast_recommendations", args=[podcast.id, podcast.slug])
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["podcast"], podcast)
        self.assertEqual(len(resp.context_data["recommendations"]), 3)


class PodcastEpisodeListTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcast = PodcastFactory()
        EpisodeFactory.create_batch(3, podcast=cls.podcast)

    def setUp(self) -> None:
        self.url = reverse(
            "podcasts:podcast_episodes",
            args=[self.podcast.id, self.podcast.slug],
        )

    def test_get_podcast(self) -> None:
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["podcast"], self.podcast)

    def test_get_episodes(self) -> None:
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 3)


class PodcastEpisodeSearchTests(TransactionTestCase):
    def test_search(self) -> None:
        podcast = PodcastFactory()
        EpisodeFactory(title="testing", podcast=podcast)
        resp = self.client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[podcast.id, podcast.slug],
            ),
            {"q": "testing"},
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class CategoryListTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.parents = CategoryFactory.create_batch(3, parent=None)

    def setUp(self) -> None:
        self.url = reverse("podcasts:categories")

    def test_get(self) -> None:
        c1 = CategoryFactory(parent=self.parents[0])
        c2 = CategoryFactory(parent=self.parents[1])
        c3 = CategoryFactory(parent=self.parents[2])

        PodcastFactory(categories=[c1, self.parents[0]])
        PodcastFactory(categories=[c2, self.parents[1]])
        PodcastFactory(categories=[c3, self.parents[2]])

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["categories"]), 3)

    def test_search(self) -> None:
        c1 = CategoryFactory(parent=self.parents[0])
        c2 = CategoryFactory(parent=self.parents[1])
        c3 = CategoryFactory(parent=self.parents[2], name="testing child")

        c4 = CategoryFactory(name="testing parent")

        PodcastFactory(categories=[c1])
        PodcastFactory(categories=[c2])
        PodcastFactory(categories=[c3])
        PodcastFactory(categories=[c4])

        resp = self.client.get(self.url, {"q": "testing"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["categories"]), 2)


class CategoryDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.category = CategoryFactory()

    def test_get(self) -> None:

        CategoryFactory.create_batch(3, parent=self.category)
        PodcastFactory.create_batch(12, categories=[self.category])
        resp = self.client.get(self.category.get_absolute_url())
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context_data["category"], self.category)

    def test_get_episodes(self) -> None:

        CategoryFactory.create_batch(3, parent=self.category)
        PodcastFactory.create_batch(12, categories=[self.category])
        resp = self.client.get(self.category.get_absolute_url())
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 12)

    def test_search(self) -> None:

        CategoryFactory.create_batch(3, parent=self.category)
        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[self.category]
        )
        PodcastFactory(title="testing", categories=[self.category])

        resp = self.client.get(self.category.get_absolute_url(), {"q": "testing"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(len(resp.context_data["page_obj"].object_list), 1)


class FollowTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcast = PodcastFactory()
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.url = reverse("podcasts:follow", args=[self.podcast.id])
        self.client.force_login(self.user)

    def test_subscribe(self) -> None:
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(
            Follow.objects.filter(podcast=self.podcast, user=self.user).exists()
        )

    def test_already_following(self) -> None:
        FollowFactory(user=self.user, podcast=self.podcast)
        self.assertEqual(
            self.client.post(self.url).status_code,
            http.HTTPStatus.OK,
        )


class UnfollowTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcast = PodcastFactory()
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_unsubscribe(self) -> None:
        FollowFactory(user=self.user, podcast=self.podcast)
        resp = self.client.post(reverse("podcasts:unfollow", args=[self.podcast.id]))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(
            Follow.objects.filter(podcast=self.podcast, user=self.user).exists()
        )


class ITunesCategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.category = CategoryFactory(itunes_genre_id=1200)

    def setUp(self) -> None:
        self.url = reverse("podcasts:itunes_category", args=[self.category.id])

    @patch(
        "audiotrails.podcasts.views.sync_podcast_feed.delay",
    )
    @patch.object(
        itunes,
        "fetch_itunes_genre",
        mock_fetch_itunes_genre,
    )
    def test_get(self, mock: Mock) -> None:
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["error"])
        self.assertEqual(len(resp.context_data["results"]), 1)
        self.assertEqual(resp.context_data["results"][0].title, "test title")

    @patch.object(
        itunes, "fetch_itunes_genre", side_effect=itunes.Invalid, autospec=True
    )
    def test_invalid_results(self, mock: Mock) -> None:

        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(resp.context_data["error"])
        self.assertEqual(len(resp.context_data["results"]), 0)


class SearchITunesTests(TestCase):
    def setUp(self) -> None:
        self.url = reverse("podcasts:search_itunes")

    def test_search_is_empty(self) -> None:
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["error"])
        self.assertEqual(len(resp.context_data["results"]), 0)

    @patch(
        "audiotrails.podcasts.views.sync_podcast_feed.delay",
    )
    @patch.object(itunes, "search_itunes", mock_search_itunes)
    def test_search(self, mock: Mock) -> None:
        resp = self.client.get(self.url, {"q": "test"})

        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertFalse(resp.context_data["error"])
        self.assertEqual(len(resp.context_data["results"]), 1)
        self.assertEqual(resp.context_data["results"][0].title, "test title")

    @patch.object(itunes, "search_itunes", side_effect=itunes.Invalid, autospec=True)
    def test_invalid_results(self, mock: Mock) -> None:
        resp = self.client.get(self.url, {"q": "testing"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(resp.context_data["error"])
        self.assertEqual(len(resp.context_data["results"]), 0)
