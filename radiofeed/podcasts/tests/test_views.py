from __future__ import annotations

import http

import pytest
import requests

from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains

from radiofeed.asserts import assert_conflict, assert_not_found, assert_ok
from radiofeed.episodes.factories import create_episode
from radiofeed.factories import create_batch
from radiofeed.podcasts import itunes
from radiofeed.podcasts.factories import (
    create_category,
    create_podcast,
    create_recommendation,
    create_subscription,
)
from radiofeed.podcasts.models import Subscription

podcasts_url = reverse_lazy("podcasts:index")


class TestLandingPage:
    url = reverse_lazy("podcasts:landing_page")

    def test_anonymous(self, client, db):
        create_batch(create_podcast, 3, promoted=True)
        response = client.get(self.url)
        assert_ok(response)

        assert len(response.context["podcasts"]) == 3

    def test_authenticated(self, client, auth_user):
        # should redirect to podcasts index page
        response = client.get(self.url)
        assert response.url == podcasts_url


class TestPodcasts:
    def test_htmx(self, client, auth_user):
        create_batch(create_podcast, 3, promoted=True)
        response = client.get(
            podcasts_url, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="pagination"
        )
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    def test_empty(self, client, auth_user):
        response = client.get(podcasts_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    def test_invalid_page(self, client, auth_user):
        response = client.get(podcasts_url, {"page": 1000})
        assert_ok(response)

    def test_user_is_subscribed_promoted(self, client, auth_user):
        """If user is not subscribed any podcasts, just show general feed"""

        create_batch(create_podcast, 3, promoted=True)
        sub = create_subscription(subscriber=auth_user).podcast
        response = client.get(reverse("podcasts:index"), {"promoted": True})
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 3
        assert sub not in response.context["page_obj"].object_list
        assert response.context["promoted"]
        assert response.context["has_subscriptions"]

    def test_user_is_not_subscribed(self, client, auth_user):
        """If user is not subscribed any podcasts, just show general feed"""

        create_batch(create_podcast, 3, promoted=True)
        response = client.get(podcasts_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    def test_user_is_subscribed(self, client, auth_user):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        create_batch(create_podcast, 3)
        sub = create_subscription(subscriber=auth_user)
        response = client.get(podcasts_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == sub.podcast
        assert not response.context["promoted"]
        assert response.context["has_subscriptions"]


class TestLatestEpisode:
    def test_no_episode(self, client, auth_user, podcast):
        assert_not_found(client.get(podcast.get_latest_episode_url()))

    def test_ok(self, client, auth_user, episode):
        assert (
            client.get(episode.podcast.get_latest_episode_url()).url
            == episode.get_absolute_url()
        )


class TestSearchPodcasts:
    url = reverse_lazy("podcasts:search_podcasts")

    def test_search_empty(self, client, auth_user):
        assert client.get(self.url, {"query": ""}).url == podcasts_url

    def test_search(self, client, auth_user, faker):
        podcast = create_podcast(title=faker.unique.text())
        create_batch(create_podcast, 3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast

    def test_search_no_results(self, client, auth_user, faker):
        response = client.get(self.url, {"query": "zzzz"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0


class TestSearchItunes:
    def test_empty(self, client, auth_user):
        response = client.get(reverse("podcasts:search_itunes"), {"query": ""})
        assert response.url == reverse("podcasts:index")

    def test_search(self, client, auth_user, podcast, mocker):
        feeds = [
            itunes.Feed(
                url="https://example.com/id123456",
                rss="https://feeds.fireside.fm/testandcode/rss",
                title="Test & Code : Py4hon Testing",
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
            ),
            itunes.Feed(
                url=podcast.link,
                rss=podcast.rss,
                title=podcast.title,
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
                podcast=podcast,
            ),
        ]
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search", return_value=feeds
        )

        response = client.get(reverse("podcasts:search_itunes"), {"query": "test"})
        assert_ok(response)

        assert response.context["feeds"] == feeds
        mock_search.assert_called()

    def test_search_exception(self, client, auth_user, mocker):
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search",
            side_effect=requests.RequestException("oops"),
        )

        response = client.get(reverse("podcasts:search_itunes"), {"query": "test"})
        assert_ok(response)

        assert response.context["feeds"] == []

        mock_search.assert_called()


class TestPodcastSimilar:
    def test_get(self, client, auth_user, podcast):
        create_batch(create_episode, 3, podcast=podcast)
        create_batch(create_recommendation, 3, podcast=podcast)
        response = client.get(
            reverse("podcasts:podcast_similar", args=[podcast.id, podcast.slug])
        )
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert len(response.context["recommendations"]) == 3


class TestPodcastDetail:
    @pytest.fixture
    def podcast(self, db, faker):
        return create_podcast(
            owner=faker.name(),
            link=faker.url(),
            funding_url=faker.url(),
            funding_text=faker.text(),
            keywords=faker.text(),
            categories=create_batch(create_category, 3),
        )

    def test_get_podcast_no_link(self, client, auth_user, faker):
        podcast = create_podcast(link=None, owner=faker.name())
        response = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert_ok(response)
        assert response.context["podcast"] == podcast

    def test_get_podcast_subscribed(self, client, auth_user, podcast):
        podcast.categories.set(create_batch(create_category, 3))
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    def test_get_podcast_not_subscribed(self, client, auth_user, podcast):
        response = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    def test_get_podcast_admin(self, client, staff_user, podcast):
        response = client.get(
            reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug])
        )
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assertContains(response, "Admin")


class TestPodcastEpisodes:
    def url(self, podcast):
        return reverse(
            "podcasts:podcast_episodes",
            args=[podcast.id, podcast.slug],
        )

    def test_get_episodes(self, client, auth_user, podcast):
        create_batch(create_episode, 33, podcast=podcast)

        response = client.get(self.url(podcast))
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 30

    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(self.url(podcast))
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0

    def test_ascending(self, client, auth_user, podcast):
        create_batch(create_episode, 33, podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"order": "asc"},
        )
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 30

    def test_search(self, client, auth_user, podcast, faker):
        create_batch(create_episode, 3, podcast=podcast)

        episode = create_episode(title=faker.unique.name(), podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"query": episode.title},
        )
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1


class TestCategoryList:
    url = reverse_lazy("podcasts:category_list")

    def test_matching_podcasts(self, client, auth_user):
        for _ in range(3):
            category = create_category()
            category.podcasts.add(create_podcast())

        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["categories"]) == 3

    def test_no_matching_podcasts(
        self,
        client,
        auth_user,
    ):
        create_batch(create_category, 3)
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["categories"]) == 0

    def test_search(self, client, auth_user, category, faker):
        create_batch(create_category, 3)

        category = create_category(name="testing")
        category.podcasts.add(create_podcast())

        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["categories"]) == 1

    def test_search_no_matching_podcasts(self, client, auth_user, category, faker):
        create_batch(create_category, 3)

        create_category(name="testing")

        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["categories"]) == 0


class TestCategoryDetail:
    def test_get(self, client, auth_user, category):
        create_batch(create_podcast, 12, categories=[category])
        response = client.get(category.get_absolute_url())
        assert_ok(response)
        assert response.context["category"] == category

    def test_search(self, client, auth_user, category, faker):
        create_batch(
            create_podcast, 12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = create_podcast(title=faker.unique.text(), categories=[category])

        response = client.get(category.get_absolute_url(), {"query": podcast.title})
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1

    def test_no_podcasts(self, client, auth_user, category):
        response = client.get(category.get_absolute_url())
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0


class TestSubscribe:
    def url(self, podcast):
        return reverse("podcasts:subscribe", args=[podcast.id])

    def test_subscribe(self, client, podcast, auth_user):
        response = client.post(
            self.url(podcast),
            HTTP_HX_TARGET=podcast.get_subscribe_target(),
            HTTP_HX_REQUEST="true",
        )
        assert_ok(response)
        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    def test_already_subscribed(
        self,
        transactional_db,
        client,
        podcast,
        auth_user,
    ):
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.post(
            self.url(podcast),
            HTTP_HX_TARGET=podcast.get_subscribe_target(),
            HTTP_HX_REQUEST="true",
        )
        assert_conflict(response)
        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()


class TestUnsubscribe:
    def test_unsubscribe(self, client, auth_user, podcast):
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.post(
            reverse("podcasts:unsubscribe", args=[podcast.id]),
            HTTP_HX_TARGET=podcast.get_subscribe_target(),
            HTTP_HX_REQUEST="true",
        )
        assert_ok(response)
        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()


class TestWebsubCallback:
    @pytest.fixture
    def feed_parser(self, mocker):
        return mocker.patch("radiofeed.feedparser.feed_parser.FeedParser.parse")

    def get_url(self, podcast):
        return reverse("podcasts:websub_callback", args=[podcast.id])

    def test_post(self, client, mocker, feed_parser, podcast):
        mocker.patch("radiofeed.podcasts.subscriber.check_signature", return_value=True)

        response = client.post(self.get_url(podcast))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        feed_parser.assert_called()

    def test_post_invalid_signature(self, client, mocker, feed_parser, podcast):
        mocker.patch(
            "radiofeed.podcasts.subscriber.check_signature", return_value=False
        )

        response = client.post(self.get_url(podcast))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        feed_parser.assert_not_called()

    def test_get(self, client, podcast):
        response = client.get(
            self.get_url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "OK",
                "hub.topic": podcast.rss,
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.OK

        podcast.refresh_from_db()

        assert podcast.websub_expires

    def test_get_denied(self, client, podcast):
        response = client.get(
            self.get_url(podcast),
            {
                "hub.mode": "denied",
                "hub.challenge": "OK",
                "hub.topic": podcast.rss,
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.OK

        podcast.refresh_from_db()

        assert podcast.websub_expires is None

    def test_get_invalid_topic(self, client, podcast):
        response = client.get(
            self.get_url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "OK",
                "hub.topic": "https://wrong-topic.com/",
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        podcast.refresh_from_db()

        assert podcast.websub_expires is None

    def test_get_invalid_lease_seconds(self, client, podcast):
        response = client.get(
            self.get_url(podcast),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "OK",
                "hub.topic": podcast.rss,
                "hub.lease_seconds": "invalid",
            },
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        podcast.refresh_from_db()

        assert podcast.websub_expires is None

    def test_get_missing_mode(self, client, podcast):
        response = client.get(
            self.get_url(podcast),
            {
                "hub.challenge": "OK",
                "hub.topic": podcast.rss,
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        podcast.refresh_from_db()

        assert podcast.websub_expires is None
