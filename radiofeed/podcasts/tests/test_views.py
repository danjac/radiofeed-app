import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains, assertTemplateUsed

from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.tests.asserts import assert200, assert404, assert409

_subscriptions_url = reverse_lazy("podcasts:subscriptions")
_discover_url = reverse_lazy("podcasts:discover")


class TestSubscriptions:
    @pytest.mark.django_db
    def test_authenticated_no_subscriptions(self, client, auth_user):
        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(_subscriptions_url)
        assert200(response)

        assertTemplateUsed(response, "podcasts/subscriptions.html")

    @pytest.mark.django_db
    def test_user_is_subscribed(self, client, auth_user):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(_subscriptions_url)

        assert200(response)

        assertTemplateUsed(response, "podcasts/subscriptions.html")

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == sub.podcast

    @pytest.mark.django_db
    def test_htmx_request(self, client, auth_user):
        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(
            _subscriptions_url,
            headers={
                "HX-Request": "true",
                "HX-Target": "pagination",
            },
        )

        assert200(response)

        assertContains(response, 'id="pagination"')

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == sub.podcast

    @pytest.mark.django_db
    def test_user_is_subscribed_search(self, client, auth_user):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(_subscriptions_url, {"search": sub.podcast.title})

        assert200(response)

        assertTemplateUsed(response, "podcasts/subscriptions.html")

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == sub.podcast


class TestDiscover:
    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(_discover_url)
        assert200(response)
        assertTemplateUsed(response, "podcasts/discover.html")

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(_discover_url)
        assert200(response)
        assertTemplateUsed(response, "podcasts/discover.html")

        assert len(response.context["podcasts"]) == 0


class TestSearchPodcasts:
    url = reverse_lazy("podcasts:search_podcasts")

    @pytest.mark.django_db
    def test_search(self, client, auth_user, faker):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"search": podcast.title})

        assert200(response)

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == podcast

    @pytest.mark.django_db
    def test_search_value_empty(self, client, auth_user, faker):
        response = client.get(self.url, {"search": ""})
        assert response.url == _discover_url

    @pytest.mark.django_db
    def test_search_filter_private(self, client, auth_user, faker):
        podcast = PodcastFactory(title=faker.unique.text(), private=True)
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        response = client.get(self.url, {"search": podcast.title})

        assert200(response)

        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_search_no_results(self, client, auth_user, faker):
        response = client.get(self.url, {"search": "zzzz"})
        assert200(response)
        assert len(response.context["page"].object_list) == 0


class TestSearchItunes:
    url = reverse_lazy("podcasts:search_itunes")

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(self.url, {"search": ""})
        assert response.url == _discover_url

    @pytest.mark.django_db
    def test_search(self, client, auth_user, podcast, mocker):
        feeds = iter(
            [
                itunes.Feed(
                    url="https://example.com/id123456",
                    rss="https://feeds.fireside.fm/testandcode/rss",
                    title="Test & Code : Python Testing",
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
        )
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search", return_value=feeds
        )

        response = client.get(self.url, {"search": "test"})
        assert200(response)

        assertTemplateUsed(response, "podcasts/search_itunes.html")

        assertContains(response, "Test &amp; Code : Python Testing")
        assertContains(response, podcast.title)

        mock_search.assert_called()


class TestPodcastSimilar:
    @pytest.mark.django_db
    def test_get(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        response = client.get(podcast.get_similar_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert len(response.context["recommendations"]) == 3


class TestPodcastDetail:
    @pytest.fixture
    def podcast(self, faker):
        return PodcastFactory(
            owner=faker.name(),
            website=faker.url(),
            funding_url=faker.url(),
            funding_text=faker.text(),
            keywords=faker.text(),
            categories=CategoryFactory.create_batch(3),
        )

    @pytest.mark.django_db
    def test_get_podcast_no_website(self, client, auth_user, faker):
        podcast = PodcastFactory(website="", owner=faker.name())
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast

    @pytest.mark.django_db
    def test_get_podcast_subscribed(self, client, auth_user, podcast):
        podcast.categories.set(CategoryFactory.create_batch(3))
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db
    def test_get_podcast_private_subscribed(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db
    def test_get_podcast_private_not_subscribed(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db
    def test_get_podcast_not_subscribed(self, client, auth_user, podcast):
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db
    def test_get_podcast_admin(self, client, staff_user, podcast):
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assertContains(response, "Admin")


class TestLatestEpisode:
    @pytest.mark.django_db
    def test_ok(self, client, auth_user, episode):
        response = client.get(self.url(episode.podcast))
        assert response.url == episode.get_absolute_url()

    @pytest.mark.django_db
    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(self.url(podcast))
        assert404(response)

    def url(self, podcast):
        return reverse("podcasts:latest_episode", args=[podcast.pk])


class TestPodcastEpisodes:
    @pytest.mark.django_db
    def test_get_episodes(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(podcast.get_episodes_url())
        assert200(response)

        assert len(response.context["page"].object_list) == 30
        assert response.context["ordering"] == "desc"

    @pytest.mark.django_db
    def test_get_episodes_for_season(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(20, podcast=podcast, season=1)
        EpisodeFactory.create_batch(10, podcast=podcast, season=2)

        response = client.get(f"{podcast.get_episodes_url()}?season=1")
        assert200(response)

        assert len(response.context["page"].object_list) == 20
        assert response.context["ordering"] == "desc"

    @pytest.mark.django_db
    def test_serial(self, client, auth_user):
        podcast = PodcastFactory(podcast_type=Podcast.PodcastType.SERIAL)
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(podcast.get_episodes_url())
        assert200(response)

        assert len(response.context["page"].object_list) == 30
        assert response.context["ordering"] == "asc"

    @pytest.mark.django_db
    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(podcast.get_episodes_url())

        assert200(response)
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_ascending(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(
            podcast.get_episodes_url(),
            {"order": "asc"},
        )
        assert200(response)

        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_search(self, client, auth_user, podcast, faker):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        response = client.get(
            podcast.get_episodes_url(),
            {"search": episode.title},
        )
        assert200(response)
        assert len(response.context["page"].object_list) == 1


class TestCategoryList:
    url = reverse_lazy("podcasts:category_list")

    @pytest.mark.django_db
    def test_matching_podcasts(self, client, auth_user):
        for _ in range(3):
            category = CategoryFactory()
            category.podcasts.add(PodcastFactory())

        response = client.get(self.url)

        assert200(response)
        assert len(response.context["categories"]) == 3

    @pytest.mark.django_db
    def test_no_matching_podcasts(
        self,
        client,
        auth_user,
    ):
        CategoryFactory.create_batch(3)
        response = client.get(self.url)

        assert200(response)
        assert len(response.context["categories"]) == 0

    @pytest.mark.django_db
    def test_search(self, client, auth_user, category, faker):
        CategoryFactory.create_batch(3)

        category = CategoryFactory(name="testing")
        category.podcasts.add(PodcastFactory())

        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assert len(response.context["categories"]) == 1

    @pytest.mark.django_db
    def test_search_no_matching_podcasts(self, client, auth_user, category, faker):
        CategoryFactory.create_batch(3)

        CategoryFactory(name="testing")

        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assert len(response.context["categories"]) == 0


class TestCategoryDetail:
    @pytest.mark.django_db
    def test_get(self, client, auth_user, category):
        PodcastFactory.create_batch(12, categories=[category])
        response = client.get(category.get_absolute_url())
        assert200(response)
        assert response.context["category"] == category

    @pytest.mark.django_db
    def test_search(self, client, auth_user, category, faker):
        PodcastFactory.create_batch(
            12, title="zzzz", keywords="zzzz", categories=[category]
        )
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        response = client.get(category.get_absolute_url(), {"search": podcast.title})

        assert200(response)

        assert len(response.context["page"].object_list) == 1

    @pytest.mark.django_db
    def test_no_podcasts(self, client, auth_user, category):
        response = client.get(category.get_absolute_url())
        assert200(response)

        assert len(response.context["page"].object_list) == 0


class TestSubscribe:
    @pytest.mark.django_db
    def test_subscribe(self, client, podcast, auth_user):
        response = client.post(
            self.url(podcast),
            headers={
                "HX-Request": "true",
            },
        )

        assert200(response)
        assertContains(response, 'id="subscribe-button"')

        assert Subscription.objects.filter(
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
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert409(response)

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db
    def test_subscribe_private(self, client, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.post(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert404(response)

        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    def url(self, podcast):
        return reverse("podcasts:subscribe", args=[podcast.pk])


class TestUnsubscribe:
    @pytest.mark.django_db
    def test_unsubscribe(self, client, auth_user, podcast):
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.delete(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert200(response)
        assertContains(response, 'id="subscribe-button"')

        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db
    def test_unsubscribe_private(self, client, auth_user):
        podcast = SubscriptionFactory(
            subscriber=auth_user, podcast=PodcastFactory(private=True)
        ).podcast

        response = client.delete(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert404(response)

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    def url(self, podcast):
        return reverse("podcasts:unsubscribe", args=[podcast.pk])


class TestPrivateFeeds:
    url = reverse_lazy("podcasts:private_feeds")

    @pytest.mark.django_db
    def test_ok(self, client, auth_user):
        for podcast in PodcastFactory.create_batch(33, private=True):
            SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(self.url)
        assert200(response)
        assert len(response.context["page"]) == 30
        assert response.context["page"].has_other_pages() is True

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        PodcastFactory(private=True)
        response = client.get(self.url)
        assert200(response)
        assert len(response.context["page"]) == 0
        assert response.context["page"].has_other_pages() is False

    @pytest.mark.django_db
    def test_search(self, client, auth_user, faker):
        podcast = SubscriptionFactory(
            subscriber=auth_user,
            podcast=PodcastFactory(title=faker.unique.text(), private=True),
        ).podcast

        SubscriptionFactory(
            subscriber=auth_user,
            podcast=PodcastFactory(title="zzz", keywords="zzzz", private=True),
        )

        response = client.get(self.url, {"search": podcast.title})
        assert200(response)

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == podcast


class TestRemovePrivateFeed:
    @pytest.mark.django_db
    def test_ok(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)

        response = client.delete(
            self.url(podcast),
            {"rss": podcast.rss},
        )
        assert response.url == reverse("podcasts:private_feeds")

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db
    def test_not_private_feed(self, client, auth_user):
        podcast = PodcastFactory(private=False)
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)
        response = client.delete(self.url(podcast), {"rss": podcast.rss})
        assert404(response)

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    def url(self, podcast):
        return reverse("podcasts:remove_private_feed", args=[podcast.pk])


class TestAddPrivateFeed:
    url = reverse_lazy("podcasts:add_private_feed")

    @pytest.fixture
    def rss(self, faker):
        return faker.url()

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "podcasts/private_feed_form.html")

    @pytest.mark.django_db
    def test_post_not_existing(self, client, auth_user, rss):
        response = client.post(self.url, {"rss": rss})
        assert response.url == reverse("podcasts:private_feeds")

        podcast = Subscription.objects.get(
            subscriber=auth_user, podcast__rss=rss
        ).podcast

        assert podcast.private

    @pytest.mark.django_db
    def test_existing_private(self, client, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.post(self.url, {"rss": podcast.rss})
        assert response.url == podcast.get_absolute_url()

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db
    def test_existing_public(self, client, auth_user):
        podcast = PodcastFactory(private=False)

        response = client.post(self.url, {"rss": podcast.rss})
        assert200(response)

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()
