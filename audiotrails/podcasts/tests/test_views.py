import http

from unittest.mock import patch

from django.test import TestCase
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
from ..models import Follow


class TestPodcastCoverImage(TestCase):
    def test_get(self):
        podcast = PodcastFactory()
        resp = self.client.get(
            reverse("podcasts:podcast_cover_image", args=[podcast.id])
        )
        assert resp.status_code == http.HTTPStatus.OK


class AnonymousPodcastsTests(TestCase):
    def test_anonymous(self):
        PodcastFactory.create_batch(3, promoted=True)
        resp = self.client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3


class AuthenticatedPodcastsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_user_is_following_featured(self):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = FollowFactory(user=self.user).podcast
        resp = self.client.get(
            reverse("podcasts:featured"), HTTP_TURBO_FRAME="podcasts"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3
        assert sub not in resp.context_data["page_obj"].object_list

    def test_user_is_not_following(self):
        """If user is not following any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        resp = self.client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following(self):
        """If user following any podcasts, show only own feed with these pdocasts"""

        PodcastFactory.create_batch(3)
        sub = FollowFactory(user=self.user)
        resp = self.client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast


class SearchPodcastsTests(TestCase):
    def test_search_empty(self):
        resp = self.client.get(
            reverse("podcasts:search_podcasts"), {"q": ""}, HTTP_TURBO_FRAME="podcasts"
        )
        assert resp.url == reverse("podcasts:index")

    def test_search(self):
        podcast = PodcastFactory(title="testing")
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        resp = self.client.get(
            reverse("podcasts:search_podcasts"),
            {"q": "testing"},
            HTTP_TURBO_FRAME="podcasts",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast


class PodcastRecommendationsTests(TestCase):
    def test_get(self):
        podcast = PodcastFactory()
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        resp = self.client.get(
            reverse("podcasts:podcast_recommendations", args=[podcast.id, podcast.slug])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["recommendations"]) == 3


class PreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.podcast = PodcastFactory()

    def setUp(self):
        self.client.force_login(self.user)

    def test_not_turbo_frame(self):
        resp = self.client.get(reverse("podcasts:preview", args=[self.podcast.id]))
        assert resp.url == self.podcast.get_absolute_url()

    def test_authenticated(self):
        EpisodeFactory.create_batch(3, podcast=self.podcast)
        resp = self.client.get(
            reverse("podcasts:preview", args=[self.podcast.id]),
            HTTP_TURBO_FRAME="modal",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == self.podcast
        assert not resp.context_data["is_following"]

    def test_following(self):
        EpisodeFactory.create_batch(3, podcast=self.podcast)
        FollowFactory(podcast=self.podcast, user=self.user)
        resp = self.client.get(
            reverse("podcasts:preview", args=[self.podcast.id]),
            HTTP_TURBO_FRAME="modal",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == self.podcast
        assert resp.context_data["is_following"]


class PodcastEpisodeListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.podcast = PodcastFactory()
        EpisodeFactory.create_batch(3, podcast=cls.podcast)

    def test_legacy_redirect(self):
        resp = self.client.get(
            f"/podcasts/{self.podcast.id}/{self.podcast.slug}/episodes/"
        )
        assert resp.status_code == http.HTTPStatus.MOVED_PERMANENTLY
        assert resp.url == reverse(
            "podcasts:podcast_episodes",
            args=[self.podcast.id, self.podcast.slug],
        )

    def test_get_podcast(self):
        resp = self.client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[self.podcast.id, self.podcast.slug],
            )
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == self.podcast

    def test_get_episodes(self):
        resp = self.client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[self.podcast.id, self.podcast.slug],
            ),
            HTTP_TURBO_FRAME="episodes",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self):
        EpisodeFactory(title="testing", podcast=self.podcast)
        resp = self.client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[self.podcast.id, self.podcast.slug],
            ),
            {"q": "testing"},
            HTTP_TURBO_FRAME="episodes",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestCategoryList:
    def test_get(self, client):
        parents = CategoryFactory.create_batch(3, parent=None)
        c1 = CategoryFactory(parent=parents[0])
        c2 = CategoryFactory(parent=parents[1])
        c3 = CategoryFactory(parent=parents[2])

        PodcastFactory(categories=[c1, parents[0]])
        PodcastFactory(categories=[c2, parents[1]])
        PodcastFactory(categories=[c3, parents[2]])

        resp = client.get(reverse("podcasts:categories"))
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["categories"]) == 3

    def test_search(self, client):
        parents = CategoryFactory.create_batch(3, parent=None)
        c1 = CategoryFactory(parent=parents[0])
        c2 = CategoryFactory(parent=parents[1])
        c3 = CategoryFactory(parent=parents[2], name="testing child")

        c4 = CategoryFactory(name="testing parent")

        PodcastFactory(categories=[c1])
        PodcastFactory(categories=[c2])
        PodcastFactory(categories=[c3])
        PodcastFactory(categories=[c4])

        resp = client.get(reverse("podcasts:categories"), {"q": "testing"})
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["categories"]) == 2


class TestCategoryDetail:
    def test_get(self, client, category):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])
        resp = client.get(category.get_absolute_url())
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["category"] == category

    def test_get_episodes(self, client, category):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])
        resp = client.get(category.get_absolute_url(), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 12

    def test_search(self, client, category):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        PodcastFactory(title="testing", categories=[category])

        resp = client.get(
            category.get_absolute_url(), {"q": "testing"}, HTTP_TURBO_FRAME="podcasts"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestFollow:
    def test_anonymous(self, client, podcast):
        resp = client.post(reverse("podcasts:follow", args=[podcast.id]))
        assert resp.url

    def test_subscribe(self, client, login_user, podcast):
        resp = client.post(reverse("podcasts:follow", args=[podcast.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert Follow.objects.filter(podcast=podcast, user=login_user).exists()

    def test_already_following(self, client, login_user, podcast):
        FollowFactory(user=login_user, podcast=podcast)
        resp = client.post(reverse("podcasts:follow", args=[podcast.id]))
        assert resp.status_code == http.HTTPStatus.OK


class TestUnfollow:
    def test_post(self, client, podcast):
        resp = client.post(reverse("podcasts:unfollow", args=[podcast.id]))
        assert resp.url

    def test_unsubscribe(self, client, login_user, podcast):
        FollowFactory(user=login_user, podcast=podcast)
        resp = client.post(reverse("podcasts:unfollow", args=[podcast.id]))
        assert resp.status_code == http.HTTPStatus.OK
        assert not Follow.objects.filter(podcast=podcast, user=login_user).exists()


class TestITunesCategory:
    def test_get(self, client, mocker):
        category = CategoryFactory(itunes_genre_id=1200)

        def mock_fetch_itunes_genre(genre_id, num_results=20):
            return [
                SearchResult(
                    rss="http://example.com/test.xml",
                    itunes="https://apple.com/some-link",
                    image="test.jpg",
                    title="test title",
                )
            ], []

        mocker.patch(
            "audiotrails.podcasts.views.sync_podcast_feed.delay",
            autospec=True,
        )
        mocker.patch.object(
            itunes,
            "fetch_itunes_genre",
            mock_fetch_itunes_genre,
        )
        resp = client.get(
            reverse("podcasts:itunes_category", args=[category.id]),
        )

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == "test title"

    def test_invalid_results(self, client, mocker):

        category = CategoryFactory(itunes_genre_id=1200)

        mocker.patch.object(
            itunes,
            "fetch_itunes_genre",
            side_effect=itunes.Invalid,
            autospec=True,
        )

        resp = client.get(reverse("podcasts:itunes_category", args=[category.id]))

        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0


def mock_search_itunes(search_term, num_results=12):
    return [
        SearchResult(
            rss="http://example.com/test.xml",
            itunes="https://apple.com/some-link",
            image="test.jpg",
            title="test title",
        )
    ], []


class SearchITunesTests(TestCase):
    def test_search_is_empty(self):
        resp = self.client.get(reverse("podcasts:search_itunes"))
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0

    @patch(
        "audiotrails.podcasts.views.sync_podcast_feed.delay",
    )
    @patch.object(itunes, "search_itunes", mock_search_itunes)
    def test_search(self, mock):
        resp = self.client.get(reverse("podcasts:search_itunes"), {"q": "test"})

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == "test title"

    @patch.object(itunes, "search_itunes", side_effect=itunes.Invalid, autospec=True)
    def test_invalid_results(self, mock):
        resp = self.client.get(reverse("podcasts:search_itunes"), {"q": "testing"})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0
