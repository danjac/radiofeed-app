import http

import httpx
import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)

podcasts_url = reverse_lazy("podcasts:index")


class TestLandingPage:
    url = reverse_lazy("podcasts:landing_page")

    @pytest.mark.django_db()
    def test_anonymous(self, client):
        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["podcasts"]) == 3

    @pytest.mark.django_db()
    def test_authenticated(self, client, auth_user):
        # should redirect to podcasts index page
        assert client.get(self.url).url == podcasts_url


class TestPodcasts:
    @pytest.mark.django_db()
    def test_htmx(self, client, auth_user):
        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(podcasts_url)

        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        response = client.get(podcasts_url)
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["page_obj"].object_list) == 0
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_invalid_page(self, client, auth_user):
        response = client.get(podcasts_url, {"page": 1000})
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db()
    def test_next_page(self, client, auth_user):
        PodcastFactory.create_batch(33, promoted=True)
        response = client.get(reverse("podcasts:index"), {"promoted": True, "page": 2})

        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]

    @pytest.mark.django_db()
    def test_user_is_subscribed_promoted(self, client, auth_user):
        """If user is not subscribed any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(subscriber=auth_user).podcast
        response = client.get(reverse("podcasts:index"), {"promoted": True})

        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 3
        assert sub not in response.context["page_obj"].object_list
        assert response.context["promoted"]
        assert response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_user_is_not_subscribed(self, client, auth_user):
        """If user is not subscribed any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(podcasts_url)

        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_user_is_subscribed(self, client, auth_user):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(podcasts_url)

        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == sub.podcast
        assert not response.context["promoted"]
        assert response.context["has_subscriptions"]


class TestLatestEpisode:
    @pytest.mark.django_db()
    def test_no_episode(self, client, auth_user, podcast):
        response = client.get(podcast.get_latest_episode_url())
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    @pytest.mark.django_db()
    def test_ok(self, client, auth_user, episode):
        assert (
            client.get(episode.podcast.get_latest_episode_url()).url
            == episode.get_absolute_url()
        )


class TestSearchPodcasts:
    url = reverse_lazy("podcasts:search_podcasts")

    @pytest.fixture()
    def mock_itunes(self, mocker):
        return mocker.patch("radiofeed.podcasts.itunes.search")

    @pytest.mark.django_db()
    def test_search_empty(self, client, auth_user, mock_itunes):
        assert client.get(self.url, {"query": ""}).url == podcasts_url
        mock_itunes.assert_not_called()

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, faker, mock_itunes):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast
        mock_itunes.assert_not_called()

    @pytest.mark.django_db()
    def test_search_filter_private(self, client, auth_user, faker, mock_itunes):
        podcast = PodcastFactory(title=faker.unique.text(), private=True)
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 0
        mock_itunes.assert_called()

    @pytest.mark.django_db()
    def test_search_filter_private_subscribed(
        self, client, auth_user, faker, mock_itunes
    ):
        podcast = PodcastFactory(title=faker.unique.text())
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast
        mock_itunes.assert_not_called()

    @pytest.mark.django_db()
    def test_search_no_results(self, client, auth_user, faker, mock_itunes):
        response = client.get(self.url, {"query": "zzzz"})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 0
        mock_itunes.assert_called()

    @pytest.mark.django_db()
    def test_search_no_results_itunes_error(
        self, client, auth_user, faker, mock_itunes
    ):
        mock_itunes.side_effect = httpx.HTTPError("oops")
        response = client.get(self.url, {"query": "zzzz"})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 0
        mock_itunes.assert_called()


class TestPodcastSimilar:
    @pytest.mark.django_db()
    def test_get(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        response = client.get(podcast.get_similar_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast
        assert len(response.context["recommendations"]) == 3


class TestPodcastDetail:
    @pytest.fixture()
    def podcast(self, faker):
        return PodcastFactory(
            owner=faker.name(),
            website=faker.url(),
            funding_url=faker.url(),
            funding_text=faker.text(),
            keywords=faker.text(),
            categories=CategoryFactory.create_batch(3),
        )

    @pytest.mark.django_db()
    def test_get_podcast_no_website(self, client, auth_user, faker):
        podcast = PodcastFactory(website=None, owner=faker.name())
        response = client.get(podcast.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast

    @pytest.mark.django_db()
    def test_get_podcast_subscribed(self, client, auth_user, podcast):
        podcast.categories.set(CategoryFactory.create_batch(3))
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db()
    def test_get_podcast_private_subscribed(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db()
    def test_get_podcast_private_not_subscribed(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        response = client.get(podcast.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db()
    def test_get_podcast_not_subscribed(self, client, auth_user, podcast):
        response = client.get(podcast.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db()
    def test_get_podcast_admin(self, client, staff_user, podcast):
        response = client.get(podcast.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["podcast"] == podcast
        assertContains(response, "Admin")


class TestPodcastEpisodes:
    def url(self, podcast):
        return podcast.get_episodes_url()

    @pytest.mark.django_db()
    def test_get_episodes(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(self.url(podcast))
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(self.url(podcast))
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 0

    @pytest.mark.django_db()
    def test_ascending(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"order": "asc"},
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, podcast, faker):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"query": episode.title},
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 1


class TestCategoryList:
    url = reverse_lazy("podcasts:category_list")

    @pytest.mark.django_db()
    def test_matching_podcasts(self, client, auth_user):
        for _ in range(3):
            category = CategoryFactory()
            category.podcasts.add(PodcastFactory())

        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["categories"]) == 3

    @pytest.mark.django_db()
    def test_no_matching_podcasts(
        self,
        client,
        auth_user,
    ):
        CategoryFactory.create_batch(3)
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["categories"]) == 0

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, category, faker):
        CategoryFactory.create_batch(3)

        category = CategoryFactory(name="testing")
        category.podcasts.add(PodcastFactory())

        response = client.get(self.url, {"query": "testing"})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["categories"]) == 1

    @pytest.mark.django_db()
    def test_search_no_matching_podcasts(self, client, auth_user, category, faker):
        CategoryFactory.create_batch(3)

        CategoryFactory(name="testing")

        response = client.get(self.url, {"query": "testing"})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["categories"]) == 0


class TestCategoryDetail:
    @pytest.mark.django_db()
    def test_get(self, client, auth_user, category):
        PodcastFactory.create_batch(12, categories=[category])
        response = client.get(category.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK
        assert response.context["category"] == category

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, category, faker):
        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        response = client.get(category.get_absolute_url(), {"query": podcast.title})
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["page_obj"].object_list) == 1

    @pytest.mark.django_db()
    def test_no_podcasts(self, client, auth_user, category):
        response = client.get(category.get_absolute_url())
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.context["page_obj"].object_list) == 0


class TestSubscribe:
    def url(self, podcast):
        return reverse("podcasts:subscribe", args=[podcast.pk])

    @pytest.mark.django_db()
    def test_subscribe(self, client, podcast, auth_user):
        response = client.post(self.url(podcast), HTTP_HX_REQUEST="true")

        assert response.status_code == http.HTTPStatus.OK

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db()
    def test_subscribe_private(self, client, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.post(self.url(podcast), HTTP_HX_REQUEST="true")

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db()(transaction=True)
    def test_already_subscribed(
        self,
        client,
        podcast,
        auth_user,
    ):
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.post(
            self.url(podcast),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == http.HTTPStatus.CONFLICT
        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()


class TestUnsubscribe:
    def url(self, podcast):
        return reverse("podcasts:unsubscribe", args=[podcast.pk])

    @pytest.mark.django_db()
    def test_unsubscribe(self, client, auth_user, podcast):
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.delete(
            self.url(podcast),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db()
    def test_unsubscribe_private(self, client, auth_user):
        podcast = SubscriptionFactory(
            subscriber=auth_user, podcast=PodcastFactory(private=True)
        ).podcast

        response = client.delete(self.url(podcast), HTTP_HX_REQUEST="true")
        assert response.status_code == http.HTTPStatus.NOT_FOUND

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()


class TestPrivateFeeds:
    url = reverse_lazy("podcasts:private_feeds")

    @pytest.mark.django_db()
    def test_ok(self, client, auth_user):
        for podcast in PodcastFactory.create_batch(33, private=True):
            SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        response = client.get(self.url)

        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, faker):
        podcast = SubscriptionFactory(
            subscriber=auth_user,
            podcast=PodcastFactory(title=faker.unique.text(), private=True),
        ).podcast

        SubscriptionFactory(
            subscriber=auth_user,
            podcast=PodcastFactory(title="zzz", keywords="zzzz", private=True),
        )

        response = client.get(self.url, {"query": podcast.title})
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast


class TestRemovePrivateFeed:
    @pytest.mark.django_db()
    def test_ok(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)

        response = client.delete(
            reverse("podcasts:remove_private_feed", args=[podcast.pk]),
            {"rss": podcast.rss},
        )
        assert response.url == reverse("podcasts:private_feeds")

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db()
    def test_not_private_feed(self, client, auth_user):
        podcast = PodcastFactory(private=False)
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)

        response = client.delete(
            reverse("podcasts:remove_private_feed", args=[podcast.pk]),
            {"rss": podcast.rss},
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()


class TestAddPrivateFeed:
    url = reverse_lazy("podcasts:add_private_feed")

    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db()
    def test_post_not_existing(self, client, faker, auth_user):
        rss = faker.url()
        response = client.post(self.url, {"rss": rss})
        assert response.url == reverse("podcasts:private_feeds")

        podcast = Subscription.objects.get(
            subscriber=auth_user, podcast__rss=rss
        ).podcast

        assert podcast.private

    @pytest.mark.django_db()
    def test_existing_private(self, client, faker, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.post(self.url, {"rss": podcast.rss})
        assert response.url == podcast.get_absolute_url()

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db()
    def test_existing_public(self, client, faker, auth_user):
        podcast = PodcastFactory(private=False)

        response = client.post(self.url, {"rss": podcast.rss})
        assert response.status_code == http.HTTPStatus.OK

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()
