import pytest
import requests

from django.urls import reverse, reverse_lazy

from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from jcasts.podcasts.itunes import Feed
from jcasts.podcasts.models import Subscription
from jcasts.shared.assertions import assert_conflict, assert_ok

podcasts_url = reverse_lazy("podcasts:index")


class TestPodcasts:
    def test_anonymous(self, client, db, django_assert_num_queries):
        PodcastFactory.create_batch(3, promoted=True)
        with django_assert_num_queries(3):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_subscribed_promoted(
        self, client, auth_user, django_assert_num_queries
    ):
        """If user is not subscribed any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(user=auth_user).podcast
        with django_assert_num_queries(6):
            resp = client.get(reverse("podcasts:index"), {"promoted": True})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3
        assert sub not in resp.context_data["page_obj"].object_list

    def test_user_is_not_subscribed(self, client, auth_user, django_assert_num_queries):
        """If user is not subscribed any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        with django_assert_num_queries(6):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_user_is_subscribed(self, client, auth_user, django_assert_num_queries):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3)
        sub = SubscriptionFactory(user=auth_user)
        with django_assert_num_queries(6):
            resp = client.get(podcasts_url)
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == sub.podcast


class TestSearchPodcasts:
    def test_search_empty(self, client, db, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert (
                client.get(
                    reverse("podcasts:search_podcasts"),
                    {"q": ""},
                ).url
                == podcasts_url
            )

    def test_search(self, client, db, faker, django_assert_num_queries):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        with django_assert_num_queries(3):
            resp = client.get(
                reverse("podcasts:search_podcasts"),
                {"q": podcast.title},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == podcast


class TestSearchITunes:
    def test_search(self, client, db, mocker, django_assert_num_queries):
        feeds = [
            Feed(
                url="https://feeds.fireside.fm/testandcode/rss",
                title="Test & Code : Py4hon Testing",
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
            )
        ]
        mock_search = mocker.patch("jcasts.podcasts.itunes.search", return_value=feeds)

        with django_assert_num_queries(1):
            resp = client.get(reverse("podcasts:search_itunes"), {"q": "test"})
        assert_ok(resp)

        mock_search.assert_called()

    def test_search_exception(self, client, db, mocker, django_assert_num_queries):
        mock_search = mocker.patch(
            "jcasts.podcasts.itunes.search", side_effect=requests.RequestException
        )

        with django_assert_num_queries(1):
            resp = client.get(reverse("podcasts:search_itunes"), {"q": "test"})
        assert_ok(resp)

        mock_search.assert_called()


class TestPodcastSimilar:
    def test_get(self, client, db, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        with django_assert_num_queries(5):
            resp = client.get(
                reverse("podcasts:podcast_similar", args=[podcast.id, podcast.slug])
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast
        assert len(resp.context_data["recommendations"]) == 3


class TestPodcastDetail:
    def test_get_podcast_anonymous(self, client, podcast, django_assert_num_queries):
        with django_assert_num_queries(6):
            resp = client.get(
                reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast

    def test_get_podcast_authenticated(
        self, client, auth_user, podcast, django_assert_num_queries
    ):
        with django_assert_num_queries(9):
            resp = client.get(
                reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
            )
        assert_ok(resp)
        assert resp.context_data["podcast"] == podcast


class TestPodcastEpisodes:
    def url(self, podcast):
        return reverse(
            "podcasts:podcast_episodes",
            args=[podcast.id, podcast.slug],
        )

    def test_get_episodes(self, client, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(self.url(podcast))
            assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_get_oldest_first(self, client, podcast, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                self.url(podcast),
                {"ordering": "asc"},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, client, podcast, faker, django_assert_num_queries):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        with django_assert_num_queries(6):
            resp = client.get(
                self.url(podcast),
                {"q": episode.title},
            )
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestCategoryList:
    url = reverse_lazy("podcasts:category_list")

    def test_get(self, db, client, django_assert_num_queries):
        CategoryFactory.create_batch(3)
        with django_assert_num_queries(2):
            resp = client.get(self.url)
        assert_ok(resp)

    def test_search(self, client, category, faker, django_assert_num_queries):

        CategoryFactory.create_batch(3)
        CategoryFactory(name="testing")

        with django_assert_num_queries(2):
            resp = client.get(self.url, {"q": "testing"})
        assert_ok(resp)
        assert len(resp.context_data["categories"]) == 1


class TestCategoryDetail:
    def test_get(self, client, category, django_assert_num_queries):
        PodcastFactory.create_batch(12, categories=[category])
        with django_assert_num_queries(4):
            resp = client.get(category.get_absolute_url())
        assert_ok(resp)
        assert resp.context_data["category"] == category

    def test_search(self, client, category, faker, django_assert_num_queries):

        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        with django_assert_num_queries(4):
            resp = client.get(category.get_absolute_url(), {"q": podcast.title})
        assert_ok(resp)
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestCategoryDetailRedirect:
    def test_get(self, client, category, django_assert_num_queries):
        with django_assert_num_queries(1):
            resp = client.get(
                reverse(
                    "podcasts:category_detail_redirect",
                    args=[category.id, category.slug],
                )
            )
        assert resp.url == category.get_absolute_url()


class TestSubscribe:
    @pytest.fixture
    def url(self, podcast):
        return reverse("podcasts:subscribe", args=[podcast.id])

    def test_subscribe(
        self, client, podcast, auth_user, url, django_assert_num_queries
    ):
        with django_assert_num_queries(5):
            resp = client.post(url)
        assert_ok(resp)
        assert Subscription.objects.filter(podcast=podcast, user=auth_user).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_subscribed(
        self, client, podcast, auth_user, url, django_assert_num_queries
    ):

        SubscriptionFactory(user=auth_user, podcast=podcast)
        with django_assert_num_queries(5):
            resp = client.post(url)
        assert_conflict(resp)
        assert Subscription.objects.filter(podcast=podcast, user=auth_user).exists()


class TestUnsubscribe:
    def test_unsubscribe(self, client, auth_user, podcast, django_assert_num_queries):
        SubscriptionFactory(user=auth_user, podcast=podcast)
        with django_assert_num_queries(5):
            resp = client.post(reverse("podcasts:unsubscribe", args=[podcast.id]))
        assert_ok(resp)
        assert not Subscription.objects.filter(podcast=podcast, user=auth_user).exists()
