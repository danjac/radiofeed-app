import pytest
import requests
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains

from radiofeed.episodes.tests.factories import create_episode
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.tests.factories import (
    create_category,
    create_podcast,
    create_recommendation,
    create_subscription,
)
from radiofeed.tests.asserts import (
    assert_conflict,
    assert_hx_location,
    assert_not_found,
    assert_ok,
    assert_unprocessable_entity,
)
from radiofeed.tests.factories import create_batch

podcasts_url = reverse_lazy("podcasts:index")


class TestLandingPage:
    url = reverse_lazy("podcasts:landing_page")

    @pytest.mark.django_db()
    def test_anonymous(self, client):
        create_batch(create_podcast, 3, promoted=True)
        response = client.get(self.url)
        assert_ok(response)

        assert len(response.context["podcasts"]) == 3

    @pytest.mark.django_db()
    def test_authenticated(self, client, auth_user):
        # should redirect to podcasts index page
        assert client.get(self.url).url == podcasts_url


class TestPodcasts:
    @pytest.mark.django_db()
    def test_htmx(self, client, auth_user):
        create_batch(create_podcast, 3, promoted=True)
        response = client.get(
            podcasts_url,
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="pagination",
        )

        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        response = client.get(podcasts_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_invalid_page(self, client, auth_user):
        assert_ok(client.get(podcasts_url, {"page": 1000}))

    @pytest.mark.django_db()
    def test_next_page(self, client, auth_user):
        create_batch(create_podcast, 33, promoted=True)
        response = client.get(reverse("podcasts:index"), {"promoted": True, "page": 2})
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]

    @pytest.mark.django_db()
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

    @pytest.mark.django_db()
    def test_user_is_not_subscribed(self, client, auth_user):
        """If user is not subscribed any podcasts, just show general feed"""

        create_batch(create_podcast, 3, promoted=True)
        response = client.get(podcasts_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 3
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
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
    @pytest.mark.django_db()
    def test_no_episode(self, client, auth_user, podcast):
        assert_not_found(client.get(podcast.get_latest_episode_url()))

    @pytest.mark.django_db()
    def test_ok(self, client, auth_user, episode):
        assert (
            client.get(episode.podcast.get_latest_episode_url()).url
            == episode.get_absolute_url()
        )


class TestSearchPodcasts:
    url = reverse_lazy("podcasts:search_podcasts")

    @pytest.mark.django_db()
    def test_search_empty(self, client, auth_user):
        assert client.get(self.url, {"query": ""}).url == podcasts_url

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, faker):
        podcast = create_podcast(title=faker.unique.text())
        create_batch(create_podcast, 3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast

    @pytest.mark.django_db()
    def test_search_filter_private(self, client, auth_user, faker):
        podcast = create_podcast(title=faker.unique.text(), private=True)
        create_batch(create_podcast, 3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0

    @pytest.mark.django_db()
    def test_search_filter_private_subscribed(self, client, auth_user, faker):
        podcast = create_podcast(title=faker.unique.text())
        create_subscription(podcast=podcast, subscriber=auth_user)
        create_batch(create_podcast, 3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"query": podcast.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast

    @pytest.mark.django_db()
    def test_search_no_results(self, client, auth_user, faker):
        response = client.get(self.url, {"query": "zzzz"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0


class TestSearchItunes:
    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        response = client.get(reverse("podcasts:search_itunes"), {"query": ""})
        assert response.url == reverse("podcasts:index")

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, podcast, mocker):
        feeds = [
            itunes.Feed(
                url="https://example.com/id123456",
                rss="https://feeds.fireside.fm/testandcode/rss",
                title="Test & Code : Py4hon Testing",
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
            ),
            itunes.Feed(
                url=podcast.website,
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

    @pytest.mark.django_db()
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
    @pytest.mark.django_db()
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
    @pytest.fixture()
    def podcast(self, faker):
        return create_podcast(
            owner=faker.name(),
            website=faker.url(),
            funding_url=faker.url(),
            funding_text=faker.text(),
            keywords=faker.text(),
            categories=create_batch(create_category, 3),
        )

    @pytest.mark.django_db()
    def test_get_podcast_no_website(self, client, auth_user, faker):
        podcast = create_podcast(website=None, owner=faker.name())
        response = client.get(podcast.get_absolute_url())
        assert_ok(response)
        assert response.context["podcast"] == podcast

    @pytest.mark.django_db()
    def test_get_podcast_subscribed(self, client, auth_user, podcast):
        podcast.categories.set(create_batch(create_category, 3))
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db()
    def test_get_podcast_private_subscribed(self, client, auth_user):
        podcast = create_podcast(private=True)
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db()
    def test_get_podcast_private_not_subscribed(self, client, auth_user):
        podcast = create_podcast(private=True)
        response = client.get(podcast.get_absolute_url())
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db()
    def test_get_podcast_not_subscribed(self, client, auth_user, podcast):
        response = client.get(podcast.get_absolute_url())
        assert_ok(response)
        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db()
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

    @pytest.mark.django_db()
    def test_get_episodes(self, client, auth_user, podcast):
        create_batch(create_episode, 33, podcast=podcast)

        response = client.get(self.url(podcast))
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(self.url(podcast))
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0

    @pytest.mark.django_db()
    def test_ascending(self, client, auth_user, podcast):
        create_batch(create_episode, 33, podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"order": "asc"},
        )
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
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

    @pytest.mark.django_db()
    def test_matching_podcasts(self, client, auth_user):
        for _ in range(3):
            category = create_category()
            category.podcasts.add(create_podcast())

        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["categories"]) == 3

    @pytest.mark.django_db()
    def test_no_matching_podcasts(
        self,
        client,
        auth_user,
    ):
        create_batch(create_category, 3)
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["categories"]) == 0

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, category, faker):
        create_batch(create_category, 3)

        category = create_category(name="testing")
        category.podcasts.add(create_podcast())

        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["categories"]) == 1

    @pytest.mark.django_db()
    def test_search_no_matching_podcasts(self, client, auth_user, category, faker):
        create_batch(create_category, 3)

        create_category(name="testing")

        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["categories"]) == 0


class TestCategoryDetail:
    @pytest.mark.django_db()
    def test_get(self, client, auth_user, category):
        create_batch(create_podcast, 12, categories=[category])
        response = client.get(category.get_absolute_url())
        assert_ok(response)
        assert response.context["category"] == category

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, category, faker):
        create_batch(
            create_podcast, 12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = create_podcast(title=faker.unique.text(), categories=[category])

        response = client.get(category.get_absolute_url(), {"query": podcast.title})
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1

    @pytest.mark.django_db()
    def test_no_podcasts(self, client, auth_user, category):
        response = client.get(category.get_absolute_url())
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0


class TestSubscribe:
    def url(self, podcast):
        return reverse("podcasts:subscribe", args=[podcast.id])

    @pytest.mark.django_db()
    def test_subscribe(self, client, podcast, auth_user):
        assert_ok(
            client.post(
                self.url(podcast),
                HTTP_HX_REQUEST="true",
            )
        )
        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db()
    def test_subscribe_private(self, client, auth_user):
        podcast = create_podcast(private=True)

        assert_not_found(
            client.post(
                self.url(podcast),
                HTTP_HX_REQUEST="true",
            )
        )
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
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.post(
            self.url(podcast),
            HTTP_HX_REQUEST="true",
        )
        assert_conflict(response)
        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()


class TestUnsubscribe:
    def url(self, podcast):
        return reverse("podcasts:unsubscribe", args=[podcast.id])

    @pytest.mark.django_db()
    def test_unsubscribe(self, client, auth_user, podcast):
        create_subscription(subscriber=auth_user, podcast=podcast)
        response = client.delete(
            self.url(podcast),
            HTTP_HX_REQUEST="true",
        )
        assert_ok(response)
        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db()
    def test_unsubscribe_private(self, client, auth_user):
        podcast = create_subscription(
            subscriber=auth_user, podcast=create_podcast(private=True)
        ).podcast
        assert_not_found(
            client.delete(
                self.url(podcast),
                HTTP_HX_REQUEST="true",
            )
        )
        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()


class TestPrivateFeeds:
    url = reverse_lazy("podcasts:private_feeds")

    @pytest.mark.django_db()
    def test_ok(self, client, auth_user):
        for podcast in create_batch(create_podcast, 33, private=True):
            create_subscription(subscriber=auth_user, podcast=podcast)
        assert_ok(client.get(self.url))

    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        assert_ok(client.get(self.url))

    @pytest.mark.django_db()
    def test_search(self, client, auth_user, faker):
        podcast = create_subscription(
            subscriber=auth_user,
            podcast=create_podcast(title=faker.unique.text(), private=True),
        ).podcast

        create_subscription(
            subscriber=auth_user,
            podcast=create_podcast(title="zzz", keywords="zzzz", private=True),
        )

        response = client.get(self.url, {"query": podcast.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == podcast


class TestRemovePrivateFeed:
    @pytest.mark.django_db()
    def test_ok(self, client, auth_user):
        podcast = create_podcast(private=True)
        create_subscription(podcast=podcast, subscriber=auth_user)

        response = client.delete(
            reverse("podcasts:remove_private_feed", args=[podcast.pk]),
            {"rss": podcast.rss},
            HTTP_HX_REQUEST="true",
        )
        assert_hx_location(response, {"path": reverse("podcasts:private_feeds")})

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()


class TestAddPrivateFeed:
    url = reverse_lazy("podcasts:add_private_feed")

    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        assert_ok(client.get(self.url))

    @pytest.mark.django_db()
    def test_post_not_existing(self, client, faker, auth_user):
        rss = faker.url()
        assert_hx_location(
            client.post(self.url, {"rss": rss}, HTTP_HX_REQUEST="true"),
            {
                "path": reverse("podcasts:private_feeds"),
            },
        )

        podcast = Subscription.objects.get(
            subscriber=auth_user, podcast__rss=rss
        ).podcast

        assert podcast.private

    @pytest.mark.django_db()
    def test_existing_private(self, client, faker, auth_user):
        podcast = create_podcast(private=True)

        assert_hx_location(
            client.post(self.url, {"rss": podcast.rss}, HTTP_HX_REQUEST="true"),
            {
                "path": podcast.get_absolute_url(),
            },
        )

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db()
    def test_existing_public(self, client, faker, auth_user):
        podcast = create_podcast(private=False)

        assert_unprocessable_entity(
            client.post(
                self.url,
                {"rss": podcast.rss},
                HTTP_HX_REQUEST="true",
                HTTP_HX_TARGET="private-feed-form",
            ),
        )

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()
