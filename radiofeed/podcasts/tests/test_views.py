import pytest

from django.urls import reverse, reverse_lazy

from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.podcasts import itunes
from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory, RecommendationFactory, SubscriptionFactory
from radiofeed.podcasts.models import Subscription

podcasts_url = reverse_lazy("podcasts:index")


class TestPodcasts:
    def test_anonymous(self, client, db, assert_ok):
        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(podcasts_url)
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_user_is_subscribed_promoted(self, client, auth_user, assert_ok):
        """If user is not subscribed any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        sub = SubscriptionFactory(user=auth_user).podcast
        response = client.get(reverse("podcasts:index"), {"promoted": True})
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3
        assert sub not in response.context_data["page_obj"].object_list

    def test_user_is_not_subscribed(self, client, auth_user, assert_ok):
        """If user is not subscribed any podcasts, just show general feed"""

        PodcastFactory.create_batch(3, promoted=True)
        response = client.get(podcasts_url)
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_user_is_subscribed(self, client, auth_user, assert_ok):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        PodcastFactory.create_batch(3)
        sub = SubscriptionFactory(user=auth_user)
        response = client.get(podcasts_url)
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1
        assert response.context_data["page_obj"].object_list[0] == sub.podcast


class TestLatestEpisode:
    def test_no_episode(self, client, podcast, assert_not_found):
        assert_not_found(client.get(podcast.get_latest_episode_url()))

    def test_ok(self, client, episode):
        assert client.get(episode.podcast.get_latest_episode_url()).url == episode.get_absolute_url()


class TestSearchPodcasts:
    def test_search_empty(self, client, db):
        assert (
            client.get(
                reverse("podcasts:search_podcasts"),
                {"q": ""},
            ).url
            == podcasts_url
        )

    def test_search(self, client, db, faker, assert_ok):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz", keywords="zzzz")
        response = client.get(
            reverse("podcasts:search_podcasts"),
            {"q": podcast.title},
        )
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1
        assert response.context_data["page_obj"].object_list[0] == podcast


class TestSearchITunes:
    def test_empty(self, client, db):
        response = client.get(reverse("podcasts:search_itunes"), {"q": ""})
        assert response.url == reverse("podcasts:index")

    def test_search(self, client, db, mocker, assert_ok):
        feeds = [
            itunes.Feed(
                url="https://example.com/id123456",
                rss="https://feeds.fireside.fm/testandcode/rss",
                title="Test & Code : Py4hon Testing",
                image="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
            )
        ]
        mock_search = mocker.patch("radiofeed.podcasts.itunes.search_cached", return_value=feeds)

        response = client.get(reverse("podcasts:search_itunes"), {"q": "test"})
        assert_ok(response)

        assert response.context["feeds"] == feeds
        mock_search.assert_called()

    def test_search_exception(self, client, db, mocker, assert_ok):
        mock_search = mocker.patch(
            "radiofeed.podcasts.itunes.search_cached",
            side_effect=itunes.ItunesException,
        )

        response = client.get(reverse("podcasts:search_itunes"), {"q": "test"})
        assert_ok(response)

        assert response.context["feeds"] == []

        mock_search.assert_called()


class TestPodcastSimilar:
    def test_get(self, client, db, podcast, assert_ok):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        response = client.get(reverse("podcasts:podcast_similar", args=[podcast.id, podcast.slug]))
        assert_ok(response)
        assert response.context_data["podcast"] == podcast
        assert len(response.context_data["recommendations"]) == 3


class TestPodcastDetail:
    def test_get_podcast_anonymous(self, client, podcast, assert_ok):
        response = client.get(reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug]))
        assert_ok(response)
        assert response.context_data["podcast"] == podcast

    def test_get_podcast_authenticated(self, client, auth_user, podcast, assert_ok):
        response = client.get(reverse("podcasts:podcast_detail", args=[podcast.id, podcast.slug]))
        assert_ok(response)
        assert response.context_data["podcast"] == podcast


class TestPodcastEpisodes:
    def url(self, podcast):
        return reverse(
            "podcasts:podcast_episodes",
            args=[podcast.id, podcast.slug],
        )

    def test_get_episodes(self, client, podcast, assert_ok):
        EpisodeFactory.create_batch(3, podcast=podcast)

        response = client.get(self.url(podcast))
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_get_oldest_first(self, client, podcast, assert_ok):
        EpisodeFactory.create_batch(3, podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"ordering": "asc"},
        )
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 3

    def test_search(self, client, podcast, faker, assert_ok):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        response = client.get(
            self.url(podcast),
            {"q": episode.title},
        )
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1


class TestCategoryList:
    url = reverse_lazy("podcasts:category_list")

    def test_matching_podcasts(self, db, client, assert_ok):
        for _ in range(3):
            category = CategoryFactory()
            category.podcast_set.add(PodcastFactory())

        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context_data["categories"]) == 3

    def test_no_matching_podcasts(self, db, client, assert_ok):
        CategoryFactory.create_batch(3)
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context_data["categories"]) == 0

    def test_search(self, client, category, faker, assert_ok):

        CategoryFactory.create_batch(3)

        category = CategoryFactory(name="testing")
        category.podcast_set.add(PodcastFactory())

        response = client.get(self.url, {"q": "testing"})
        assert_ok(response)
        assert len(response.context_data["categories"]) == 1

    def test_search_no_matching_podcasts(self, client, category, faker, assert_ok):

        CategoryFactory.create_batch(3)

        CategoryFactory(name="testing")

        response = client.get(self.url, {"q": "testing"})
        assert_ok(response)
        assert len(response.context_data["categories"]) == 0


class TestCategoryDetail:
    def test_get(self, client, category, assert_ok):
        PodcastFactory.create_batch(12, categories=[category])
        response = client.get(category.get_absolute_url())
        assert_ok(response)
        assert response.context_data["category"] == category

    def test_search(self, client, category, faker, assert_ok):

        PodcastFactory.create_batch(12, title="zzzz", keywords="zzzz", categories=[category])
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        response = client.get(category.get_absolute_url(), {"q": podcast.title})
        assert_ok(response)
        assert len(response.context_data["page_obj"].object_list) == 1


class TestSubscribe:
    @pytest.fixture
    def url(self, podcast):
        return reverse("podcasts:subscribe", args=[podcast.id])

    def test_subscribe(self, client, podcast, auth_user, url, assert_ok):
        response = client.post(url)
        assert_ok(response)
        assert Subscription.objects.filter(podcast=podcast, user=auth_user).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_subscribed(self, client, podcast, auth_user, url, assert_conflict):

        SubscriptionFactory(user=auth_user, podcast=podcast)
        response = client.post(url)
        assert_conflict(response)
        assert Subscription.objects.filter(podcast=podcast, user=auth_user).exists()


class TestUnsubscribe:
    def test_unsubscribe(self, client, auth_user, podcast, assert_ok):
        SubscriptionFactory(user=auth_user, podcast=podcast)
        response = client.delete(reverse("podcasts:unsubscribe", args=[podcast.id]))
        assert_ok(response)
        assert not Subscription.objects.filter(podcast=podcast, user=auth_user).exists()
