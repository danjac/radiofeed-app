import http

import pytest

from django.urls import reverse

from audiotrails.episodes.factories import EpisodeFactory

from .. import itunes
from ..factories import (
    CategoryFactory,
    FollowFactory,
    PodcastFactory,
    RecommendationFactory,
)
from ..itunes import SearchResult
from ..models import Follow

pytestmark = pytest.mark.django_db


class TestPodcastCoverImage:
    def test_get(self, client, podcast):
        resp = client.get(reverse("podcasts:podcast_cover_image", args=[podcast.id]))
        assert resp.status_code == http.HTTPStatus.OK


class TestPodcasts:
    def test_anonymous(self, client):
        PodcastFactory.create_batch(3, promoted=True)
        resp = client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following_featured(self, login_user, client):
        """If user is not following any podcasts, just show general feed"""
        PodcastFactory.create_batch(3, promoted=True)
        sub = FollowFactory(user=login_user).podcast
        resp = client.get(reverse("podcasts:featured"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3
        assert sub not in resp.context_data["page_obj"].object_list

    def test_user_is_not_following(self, login_user, client):
        """If user is not following any podcasts, just show general feed"""
        PodcastFactory.create_batch(3, promoted=True)
        resp = client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_following(self, client, login_user):
        """If user following any podcasts, show only own feed with these pdocasts"""
        PodcastFactory.create_batch(3)
        sub = FollowFactory(user=login_user)
        resp = client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast


class TestSearchPodcasts:
    def test_search_empty(self, client):
        resp = client.get(
            reverse("podcasts:search_podcasts"), {"q": ""}, HTTP_TURBO_FRAME="podcasts"
        )
        assert resp.url == reverse("podcasts:index")

    def test_search(self, client):
        podcast = PodcastFactory(title="testing")
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        resp = client.get(
            reverse("podcasts:search_podcasts"),
            {"q": "testing"},
            HTTP_TURBO_FRAME="podcasts",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast


class TestPodcastRecommendations:
    def test_get(self, client, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse("podcasts:podcast_recommendations", args=[podcast.id, podcast.slug])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["recommendations"]) == 3


class TestPreview:
    def test_not_turbo_frame(self, client, login_user, podcast):
        resp = client.get(reverse("podcasts:preview", args=[podcast.id]))
        assert resp.url == podcast.get_absolute_url()

    def test_authenticated(self, client, login_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse("podcasts:preview", args=[podcast.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert not resp.context_data["is_following"]

    def test_following(self, client, login_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        FollowFactory(podcast=podcast, user=login_user)
        resp = client.get(
            reverse("podcasts:preview", args=[podcast.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["is_following"]


class TestPodcastEpisodeList:
    def test_legacy_redirect(self, client, podcast):
        resp = client.get(f"/podcasts/{podcast.id}/{podcast.slug}/episodes/")
        assert resp.status_code == http.HTTPStatus.MOVED_PERMANENTLY
        assert resp.url == reverse(
            "podcasts:podcast_episodes", args=[podcast.id, podcast.slug]
        )

    def test_get_podcast(self, client, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[podcast.id, podcast.slug],
            )
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast

    def test_get_episodes(self, client, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[podcast.id, podcast.slug],
            ),
            HTTP_TURBO_FRAME="episodes",
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast, title="zzzz", keywords="zzzz")
        EpisodeFactory(title="testing", podcast=podcast)
        resp = client.get(
            reverse(
                "podcasts:podcast_episodes",
                args=[podcast.id, podcast.slug],
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
        assert resp.status_code == http.HTTPStatus.NO_CONTENT


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


class TestSearchITunes:
    def test_search(self, client, mocker):
        def mock_search_itunes(search_term, num_results=12):
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
            "search_itunes",
            mock_search_itunes,
        )
        resp = client.get(reverse("podcasts:search_itunes"), {"q": "test"})

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == "test title"

    def test_search_is_empty(self, client):
        resp = client.get(reverse("podcasts:search_itunes"))
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0

    def test_invalid_results(self, client, mocker):
        mocker.patch.object(
            itunes,
            "search_itunes",
            side_effect=itunes.Invalid,
            autospec=True,
        )

        resp = client.get(reverse("podcasts:search_itunes"), {"q": "testing"})

        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0
