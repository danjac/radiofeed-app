# Standard Library
import http

# Django
from django.urls import reverse

# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.episodes.factories import EpisodeFactory

# Local
from .. import itunes, views
from ..factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from ..itunes import SearchResult
from ..models import Podcast, Subscription

pytestmark = pytest.mark.django_db


class TestLandingPage:
    def test_anonymous(self, rf, anonymous_user):
        PodcastFactory.create_batch(3)
        req = rf.get(reverse("podcasts:landing_page"))
        req.user = anonymous_user
        resp = views.landing_page(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["podcasts"]) == 3

    def test_authenticated(self, rf, user):
        req = rf.get(reverse("podcasts:landing_page"))
        req.user = user
        resp = views.landing_page(req)
        assert resp.url == reverse("podcasts:podcast_list")


class TestPodcastList:
    def test_anonymous(self, rf, anonymous_user, mock_turbo):
        PodcastFactory.create_batch(3)
        req = rf.get(reverse("podcasts:podcast_list"))
        req.turbo = mock_turbo(True, "podcasts")
        req.user = anonymous_user
        req.search = ""
        resp = views.podcast_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_no_subscriptions(self, rf, user, mock_turbo):
        """If user has no subscriptions, just show general feed"""
        PodcastFactory.create_batch(3)
        req = rf.get(reverse("podcasts:podcast_list"))
        req.turbo = mock_turbo(True, "podcasts")
        req.user = user
        req.search = ""
        resp = views.podcast_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_has_subscriptions(self, rf, user, mock_turbo):
        """If user has subscriptions, show only own feed"""
        PodcastFactory.create_batch(3)
        sub = SubscriptionFactory(user=user)
        req = rf.get(reverse("podcasts:podcast_list"))
        req.turbo = mock_turbo(True, "podcasts")
        req.search = ""
        req.user = user
        resp = views.podcast_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast

    def test_search_anonymous(self, rf, anonymous_user, transactional_db, mock_turbo):
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        req = rf.get(reverse("podcasts:podcast_list"))
        req.user = anonymous_user
        req.search = "testing"
        req.turbo = mock_turbo(True, "podcasts")
        podcast = PodcastFactory(title="testing")
        resp = views.podcast_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast

    def test_search_has_subscription(self, rf, user, transactional_db, mock_turbo):
        """Ignore subscribed feeds in search"""
        PodcastFactory.create_batch(3, title="zzzz", keywords="zzzz")
        SubscriptionFactory(user=user)
        req = rf.get(reverse("podcasts:podcast_list"))
        req.user = user
        req.search = "testing"
        req.turbo = mock_turbo(True, "podcasts")
        podcast = PodcastFactory(title="testing")
        resp = views.podcast_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast


class TestPodcastRecommendations:
    def test_get(self, rf, user, podcast, site):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        req = rf.get(podcast.get_absolute_url())
        req.user = user
        req.site = site
        resp = views.podcast_recommendations(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["recommendations"]) == 3


class TestPodcastCoverImage:
    def test_get(self, rf, podcast, mock_turbo):
        req = rf.get("podcasts:podcast_cover_image", args=[podcast.id])
        req.turbo = mock_turbo(True, "cover-image")
        resp = views.podcast_cover_image(req, podcast.id)
        assert resp.status_code == http.HTTPStatus.OK


class TestPodcastDetail:
    def test_anonymous(self, rf, anonymous_user, podcast, site):
        EpisodeFactory.create_batch(3, podcast=podcast)
        req = rf.get(podcast.get_absolute_url())
        req.user = anonymous_user
        req.site = site
        resp = views.podcast_detail(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["total_episodes"] == 3
        assert not resp.context_data["is_subscribed"]

    def test_authenticated(self, rf, user, podcast, site):
        EpisodeFactory.create_batch(3, podcast=podcast)
        req = rf.get(podcast.get_absolute_url())
        req.user = user
        req.site = site
        resp = views.podcast_detail(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["total_episodes"] == 3
        assert not resp.context_data["is_subscribed"]

    def test_subscribed(self, rf, user, podcast, site):
        EpisodeFactory.create_batch(3, podcast=podcast)
        SubscriptionFactory(podcast=podcast, user=user)
        req = rf.get(podcast.get_absolute_url())
        req.user = user
        req.site = site
        resp = views.podcast_detail(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast
        assert resp.context_data["total_episodes"] == 3
        assert resp.context_data["is_subscribed"]


class TestPodcastEpisodeList:
    def test_get_podcast(self, rf, anonymous_user, podcast, site, mock_turbo):
        EpisodeFactory.create_batch(3, podcast=podcast)
        req = rf.get(
            reverse(
                "podcasts:podcast_episode_list",
                args=[podcast.id, podcast.slug],
            )
        )
        req.user = anonymous_user
        req.site = site
        req.search = ""
        req.turbo = mock_turbo(False)
        resp = views.podcast_episode_list(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["podcast"] == podcast

    def test_get_episodes(self, rf, anonymous_user, podcast, site, mock_turbo):
        EpisodeFactory.create_batch(3, podcast=podcast)
        req = rf.get(
            reverse(
                "podcasts:podcast_episode_list",
                args=[podcast.id, podcast.slug],
            )
        )
        req.user = anonymous_user
        req.site = site
        req.search = ""
        req.turbo = mock_turbo(True, "episodes")
        resp = views.podcast_episode_list(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(
        self, rf, anonymous_user, podcast, site, transactional_db, mock_turbo
    ):
        EpisodeFactory.create_batch(3, podcast=podcast, title="zzzz", keywords="zzzz")
        EpisodeFactory(title="testing", podcast=podcast)
        req = rf.get(
            reverse(
                "podcasts:podcast_episode_list",
                args=[podcast.id, podcast.slug],
            ),
        )
        req.search = "testing"
        req.turbo = mock_turbo(True, "episodes")
        req.user = anonymous_user
        req.site = site
        resp = views.podcast_episode_list(req, podcast.id, podcast.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestAddPodcast:
    def test_add_podcast(self, rf, admin_user, mocker, mock_turbo):
        data = {
            "itunes": "http://itunes.apple.com",
            "rss": "https://example.com/rss.xml",
            "title": "Example",
        }

        mock = mocker.patch("radiofeed.podcasts.views.sync_podcast_feed.delay")

        req = rf.post(reverse("podcasts:add_podcast"), data)
        req.user = admin_user
        req.turbo = mock_turbo(True, "add-btn")

        resp = views.add_podcast(req)
        assert resp.status_code == http.HTTPStatus.OK

        podcast = Podcast.objects.get()
        assert podcast.title == data["title"]
        assert podcast.rss == data["rss"]
        assert podcast.itunes == data["itunes"]

        mock.asset_called()


class TestCategoryList:
    def test_get(self, rf):
        parents = CategoryFactory.create_batch(3, parent=None)
        c1 = CategoryFactory(parent=parents[0])
        c2 = CategoryFactory(parent=parents[1])
        c3 = CategoryFactory(parent=parents[2])

        PodcastFactory(categories=[c1, parents[0]])
        PodcastFactory(categories=[c2, parents[1]])
        PodcastFactory(categories=[c3, parents[2]])

        req = rf.get(reverse("podcasts:category_list"))
        req.search = ""
        resp = views.category_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["categories"]) == 3

    def test_search(self, rf, transactional_db):
        parents = CategoryFactory.create_batch(3, parent=None)
        c1 = CategoryFactory(parent=parents[0])
        c2 = CategoryFactory(parent=parents[1])
        c3 = CategoryFactory(parent=parents[2], name="testing child")

        c4 = CategoryFactory(name="testing parent")

        PodcastFactory(categories=[c1])
        PodcastFactory(categories=[c2])
        PodcastFactory(categories=[c3])
        PodcastFactory(categories=[c4])
        req = rf.get(reverse("podcasts:category_list"))
        req.search = "testing"
        resp = views.category_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["categories"]) == 2


class TestCategoryDetail:
    def test_get(self, rf, category, anonymous_user, mock_turbo):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])
        req = rf.get(category.get_absolute_url())
        req.user = anonymous_user
        req.search = ""
        req.turbo = mock_turbo(False)
        resp = views.category_detail(req, category.id, category.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["category"] == category

    def test_get_episodes(self, rf, category, anonymous_user, mock_turbo):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(12, categories=[category])
        req = rf.get(category.get_absolute_url())
        req.user = anonymous_user
        req.turbo = mock_turbo(True, "episodes")
        req.search = ""
        resp = views.category_detail(req, category.id, category.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 12

    def test_search(self, rf, category, anonymous_user, transactional_db, mock_turbo):

        CategoryFactory.create_batch(3, parent=category)
        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        PodcastFactory(title="testing", categories=[category])

        req = rf.get(category.get_absolute_url())
        req.search = "testing"
        req.user = anonymous_user
        req.turbo = mock_turbo(True, "podcasts")
        resp = views.category_detail(req, category.id, category.slug)

        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestSubscribe:
    def test_subscribe(self, rf, podcast, user, mock_turbo):
        req = rf.post(reverse("podcasts:subscribe", args=[podcast.id]))
        req.user = user
        req.turbo = mock_turbo(True, "subscribe")
        resp = views.subscribe(req, podcast.id)
        assert resp.status_code == http.HTTPStatus.OK

    def test_already_subscribed(self, rf, podcast, user, mock_turbo):
        SubscriptionFactory(user=user, podcast=podcast)
        req = rf.post(reverse("podcasts:subscribe", args=[podcast.id]))
        req.user = user
        req.turbo = mock_turbo(True, "subscribe")
        resp = views.subscribe(req, podcast.id)
        assert resp.status_code == http.HTTPStatus.OK


class TestUnsubscribe:
    def test_unsubscribe(self, rf, podcast, user, mock_turbo):
        SubscriptionFactory(user=user, podcast=podcast)
        req = rf.post(reverse("podcasts:unsubscribe", args=[podcast.id]))
        req.user = user
        req.turbo = mock_turbo(True, "subscribe")
        resp = views.unsubscribe(req, podcast.id)
        assert resp.status_code == http.HTTPStatus.OK
        assert not Subscription.objects.filter(podcast=podcast, user=user).exists()


class TestITunesCategory:
    def test_get(self, rf, mocker):
        category = CategoryFactory(itunes_genre_id=1200)

        def mock_fetch_itunes_genre(genre_id, num_results=20):
            return [
                SearchResult(
                    rss="http://example.com/test.xml",
                    itunes="https://apple.com/some-link",
                    image="test.jpg",
                    title="test title",
                )
            ]

        mocker.patch.object(views.itunes, "fetch_itunes_genre", mock_fetch_itunes_genre)
        req = rf.get(reverse("podcasts:itunes_category", args=[category.id]))
        resp = views.itunes_category(req, category.id)

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == "test title"

    def test_invalid_results(self, rf, mocker):

        category = CategoryFactory(itunes_genre_id=1200)

        mock = mocker.patch.object(views.itunes, "fetch_itunes_genre")
        mock.side_effect = itunes.Invalid

        req = rf.get(reverse("podcasts:itunes_category", args=[category.id]))
        resp = views.itunes_category(req, category.id)

        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0


class TestSearchITunes:
    def test_search(self, rf, mocker):
        def mock_search_itunes(search_term, num_results=12):
            return [
                SearchResult(
                    rss="http://example.com/test.xml",
                    itunes="https://apple.com/some-link",
                    image="test.jpg",
                    title="test title",
                )
            ]

        mocker.patch.object(views.itunes, "search_itunes", mock_search_itunes)
        req = rf.get(reverse("podcasts:search_itunes"))
        req.search = "test"
        resp = views.search_itunes(req)

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 1
        assert resp.context_data["results"][0].title == "test title"

    def test_search_is_empty(self, rf, mocker):
        req = rf.get(reverse("podcasts:search_itunes"))
        req.search = ""
        resp = views.search_itunes(req)

        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0

    def test_invalid_results(self, rf, mocker):
        mock = mocker.patch.object(views.itunes, "search_itunes")
        mock.side_effect = itunes.Invalid
        req = rf.get(reverse("podcasts:search_itunes"))
        req.search = "test"
        resp = views.search_itunes(req)

        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["error"]
        assert len(resp.context_data["results"]) == 0
