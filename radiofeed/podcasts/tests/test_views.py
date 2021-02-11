# Standard Library
import http

# Django
from django.urls import reverse

# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.episodes.factories import EpisodeFactory

# Local
from .. import itunes
from ..factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from ..itunes import SearchResult
from ..models import Subscription

pytestmark = pytest.mark.django_db


class TestLandingPage:
    def test_anonymous(self, client):
        PodcastFactory.create_batch(3, promoted=True)
        PodcastFactory()
        resp = client.get(reverse("podcasts:landing_page"))
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["podcasts"]) == 3

    def test_authenticated(self, client, login_user):
        resp = client.get(reverse("podcasts:landing_page"))
        assert resp.url == reverse("episodes:index")


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

    def test_user_no_subscriptions(self, login_user, client):
        """If user has no subscriptions, just show general feed"""
        PodcastFactory.create_batch(3, promoted=True)
        resp = client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_has_subscriptions(self, client, login_user):
        """If user has subscriptions, show only own feed"""
        PodcastFactory.create_batch(3)
        sub = SubscriptionFactory(user=login_user)
        resp = client.get(reverse("podcasts:index"), HTTP_TURBO_FRAME="podcasts")
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast


class TestSearchEpisodes:
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


class TestPodcastActions:
    def test_not_turbo_frame(self, client, login_user, podcast):
        resp = client.get(reverse("podcasts:actions", args=[podcast.id]))
        assert resp.url == podcast.get_absolute_url()

    def test_authenticated(self, client, login_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse("podcasts:actions", args=[podcast.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert not resp.context_data["is_subscribed"]

    def test_subscribed(self, client, login_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        SubscriptionFactory(podcast=podcast, user=login_user)
        resp = client.get(
            reverse("podcasts:actions", args=[podcast.id]), HTTP_TURBO_FRAME="modal"
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["is_subscribed"]


class TestPodcastDetail:
    def test_anonymous(self, client, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["total_episodes"] == 3
        assert not resp.context_data["is_subscribed"]

    def test_authenticated(self, client, login_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        resp = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["total_episodes"] == 3
        assert not resp.context_data["is_subscribed"]

    def test_subscribed(self, client, login_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        SubscriptionFactory(podcast=podcast, user=login_user)
        resp = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["total_episodes"] == 3
        assert resp.context_data["is_subscribed"]


class TestPodcastEpisodeList:
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


class TestSubscribe:
    def test_subscribe(self, client, login_user, podcast):
        resp = client.post(reverse("podcasts:subscribe", args=[podcast.id]))
        assert resp.url == podcast.get_absolute_url()
        assert Subscription.objects.filter(podcast=podcast, user=login_user).exists()

    def test_already_subscribed(self, client, login_user, podcast):
        SubscriptionFactory(user=login_user, podcast=podcast)
        resp = client.post(reverse("podcasts:subscribe", args=[podcast.id]))
        assert resp.url == podcast.get_absolute_url()


class TestUnsubscribe:
    def test_unsubscribe(self, client, login_user, podcast):
        SubscriptionFactory(user=login_user, podcast=podcast)
        resp = client.post(reverse("podcasts:unsubscribe", args=[podcast.id]))
        assert resp.url == podcast.get_absolute_url()
        assert not Subscription.objects.filter(
            podcast=podcast, user=login_user
        ).exists()


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

        mocker.patch("radiofeed.podcasts.views.sync_podcast_feed.delay")
        mocker.patch.object(itunes, "fetch_itunes_genre", mock_fetch_itunes_genre)
        resp = client.get(reverse("podcasts:itunes_category", args=[category.id]))

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == "test title"

    def test_invalid_results(self, client, mocker):

        category = CategoryFactory(itunes_genre_id=1200)

        mocker.patch.object(itunes, "fetch_itunes_genre", side_effect=itunes.Invalid)

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

        mocker.patch("radiofeed.podcasts.views.sync_podcast_feed.delay")
        mocker.patch.object(itunes, "search_itunes", mock_search_itunes)
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
        mocker.patch.object(itunes, "search_itunes", side_effect=itunes.Invalid)

        resp = client.get(reverse("podcasts:search_itunes"), {"q": "testing"})

        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0
